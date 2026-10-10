#!/usr/bin/env python3
"""Ponte ESP32-S3 UART -> Firebase RTDB com recepção serial desacoplada da rede.

Motivação:
- A ESP32-S3 envia 250 linhas JSON/s.
- O publicador agrupa 50 amostras (~5 blocos/s).
- A chamada HTTP PUT ao Firebase pode levar dezenas/centenas de ms.
- Se a mesma thread faz readline() e PUT(), o buffer serial do host pode
  transbordar durante o PUT, causando linhas truncadas/concatenadas.

Nesta versão:
    Thread serial -> Queue RAM -> Thread principal/publicação Firebase

O relógio da aquisição permanece definido pelo sample_index gerado na ESP32.
"""

from __future__ import annotations

import argparse
import json
import os
import queue
import threading
import time
import uuid
from dataclasses import dataclass
from typing import Any

import requests
import serial

DEFAULT_NODE = "oficina/live"


def firebase_node_url(firebase_url: str, node: str = DEFAULT_NODE) -> str:
    return f"{firebase_url.rstrip('/')}/{node.strip('/')}.json"


def parse_sample(line: str) -> dict[str, Any]:
    obj = json.loads(line)

    for key in ("sample_index", "ecg", "ppg_ir", "ppg_red"):
        if key not in obj:
            raise ValueError(f"campo ausente: {key}")

    source = str(obj.get("source", "HW")).upper()
    if source not in ("HW", "SIM"):
        source = "HW"

    return {
        "sample_index": int(obj["sample_index"]),
        "ecg": float(obj["ecg"]),
        "ppg_ir": float(obj["ppg_ir"]),
        "ppg_red": float(obj["ppg_red"]),
        "source": source,
    }


@dataclass
class Stats:
    serial_lines: int = 0
    valid_samples: int = 0
    malformed_lines: int = 0
    non_json_lines: int = 0
    host_queue_drops: int = 0
    serial_gaps: int = 0
    packets_published: int = 0
    firebase_errors: int = 0


def serial_reader(
    ser: serial.Serial,
    sample_q: queue.Queue,
    stop_event: threading.Event,
    stats: Stats,
    verbose: bool,
) -> None:
    """ÚNICA rotina que lê a serial; nunca faz acesso à rede."""
    last_index: int | None = None

    while not stop_event.is_set():
        try:
            raw_bytes = ser.readline()
        except serial.SerialException as exc:
            print(f"\n[ERRO serial] {exc}")
            stop_event.set()
            return

        if not raw_bytes:
            continue

        stats.serial_lines += 1

        try:
            raw = raw_bytes.decode("utf-8", errors="strict").strip()
        except UnicodeDecodeError as exc:
            stats.malformed_lines += 1
            if verbose:
                print(f"\n[UTF-8 inválido] {exc}: {raw_bytes[:80]!r}")
            continue

        if not raw:
            continue

        if not raw.startswith("{"):
            stats.non_json_lines += 1
            if verbose:
                print(f"\n[diagnóstico ignorado] {raw[:140]}")
            continue

        try:
            sample = parse_sample(raw)
        except (json.JSONDecodeError, ValueError, KeyError) as exc:
            stats.malformed_lines += 1
            if verbose:
                print(f"\n[linha descartada] {exc}: {raw[:160]}")
            continue

        idx = sample["sample_index"]
        if last_index is not None and idx != last_index + 1:
            # Em DROPOUT esta lacuna é intencional. Em outros modos pode
            # representar perda real na cadeia serial/firmware.
            stats.serial_gaps += 1
        last_index = idx
        stats.valid_samples += 1

        try:
            sample_q.put_nowait(sample)
        except queue.Full:
            # Não bloqueia a leitura da UART. Se a rede ficar indisponível
            # por muito tempo, a perda é explícita e sample_index a revela.
            stats.host_queue_drops += 1


def montar_payload(
    session_id: str,
    packet_seq: int,
    fs: float,
    block: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "session_id": session_id,
        "seq": packet_seq,
        "sample_start": int(block[0]["sample_index"]),
        "timestamp_pub": time.time(),
        "fs": fs,
        "n": len(block),
        "source": block[0]["source"],
        "ecg": [round(float(s["ecg"]), 5) for s in block],
        "ppg_ir": [round(float(s["ppg_ir"]), 2) for s in block],
        "ppg_red": [round(float(s["ppg_red"]), 2) for s in block],
    }


def publicar_bloco(
    http: requests.Session,
    firebase_url: str,
    node: str,
    auth: str,
    session_id: str,
    packet_seq: int,
    fs: float,
    block: list[dict[str, Any]],
    timeout: float,
    retries: int,
) -> None:
    payload = montar_payload(session_id, packet_seq, fs, block)
    params = {"auth": auth} if auth else None
    url = firebase_node_url(firebase_url, node)

    last_exc: Exception | None = None
    for attempt in range(retries + 1):
        try:
            r = http.put(url, params=params, json=payload, timeout=timeout)
            r.raise_for_status()
            return
        except requests.RequestException as exc:
            last_exc = exc
            if attempt < retries:
                time.sleep(0.15 * (attempt + 1))

    assert last_exc is not None
    raise last_exc


def print_status(stats: Stats, sample_q: queue.Queue, packet_seq: int) -> None:
    print(
        f"\rpackets={packet_seq:5d} "
        f"amostras={stats.valid_samples:8d} "
        f"fila={sample_q.qsize():4d} "
        f"JSON_ruim={stats.malformed_lines:4d} "
        f"gaps={stats.serial_gaps:4d} "
        f"drop_host={stats.host_queue_drops:3d} "
        f"fb_err={stats.firebase_errors:3d}",
        end="",
        flush=True,
    )


def main() -> None:
    ap = argparse.ArgumentParser(
        description="ESP32-S3 UART -> Firebase RTDB (serial e rede desacopladas)"
    )
    ap.add_argument("--serial", required=True, help="Ex.: /dev/ttyACM1")
    ap.add_argument("--baud", type=int, default=460800)
    ap.add_argument("--url", default=os.getenv("FIREBASE_URL", ""))
    ap.add_argument("--node", default=os.getenv("FIREBASE_NODE", DEFAULT_NODE))
    ap.add_argument("--auth", default=os.getenv("FIREBASE_AUTH", ""))
    ap.add_argument("--fs", type=float, default=250.0)
    ap.add_argument("--block", type=int, default=50)
    ap.add_argument(
        "--queue-samples",
        type=int,
        default=5000,
        help="buffer RAM entre serial e Firebase (5000 ~= 20 s a 250 Hz)",
    )
    ap.add_argument("--http-timeout", type=float, default=5.0)
    ap.add_argument("--http-retries", type=int, default=1)
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="testa somente a recepção serial; não publica no Firebase",
    )
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    if not args.dry_run and not args.url:
        raise SystemExit("Informe --url/defina FIREBASE_URL ou use --dry-run")

    session_id = uuid.uuid4().hex
    stats = Stats()
    sample_q: queue.Queue = queue.Queue(maxsize=max(100, args.queue_samples))
    stop_event = threading.Event()

    print(f"Serial: {args.serial}@{args.baud}")
    if args.dry_run:
        print("Firebase: DESATIVADO (--dry-run)")
    else:
        print(f"Firebase: {firebase_node_url(args.url, args.node)}")
    print(f"Sessão: {session_id}")
    print(
        f"fs={args.fs:g} Hz; bloco={args.block}; "
        f"fila RAM={sample_q.maxsize} amostras"
    )

    packet_seq = 0
    block: list[dict[str, Any]] = []
    last_status = time.monotonic()

    with serial.Serial(
        args.serial,
        args.baud,
        timeout=0.20,
        bytesize=serial.EIGHTBITS,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
    ) as ser, requests.Session() as http:

        # Começa em uma fronteira limpa; descarta eventual lixo anterior.
        ser.reset_input_buffer()

        reader = threading.Thread(
            target=serial_reader,
            args=(ser, sample_q, stop_event, stats, args.verbose),
            name="serial-reader",
            daemon=True,
        )
        reader.start()

        try:
            while not stop_event.is_set():
                try:
                    sample = sample_q.get(timeout=0.10)
                except queue.Empty:
                    sample = None

                if sample is not None:
                    discontinuity = (
                        bool(block)
                        and sample["sample_index"]
                        != block[-1]["sample_index"] + 1
                    )
                    source_changed = (
                        bool(block)
                        and sample["source"] != block[-1]["source"]
                    )

                    if (discontinuity or source_changed) and block:
                        if not args.dry_run:
                            try:
                                publicar_bloco(
                                    http, args.url, args.node, args.auth,
                                    session_id, packet_seq, args.fs, block,
                                    args.http_timeout, args.http_retries,
                                )
                                stats.packets_published += 1
                            except requests.RequestException as exc:
                                stats.firebase_errors += 1
                                if args.verbose:
                                    print(f"\n[Firebase] {exc}")
                        packet_seq += 1
                        block = []

                    block.append(sample)

                    if len(block) >= args.block:
                        if not args.dry_run:
                            try:
                                publicar_bloco(
                                    http, args.url, args.node, args.auth,
                                    session_id, packet_seq, args.fs, block,
                                    args.http_timeout, args.http_retries,
                                )
                                stats.packets_published += 1
                            except requests.RequestException as exc:
                                stats.firebase_errors += 1
                                if args.verbose:
                                    print(f"\n[Firebase] {exc}")
                        packet_seq += 1
                        block = []

                now = time.monotonic()
                if now - last_status >= 1.0:
                    print_status(stats, sample_q, packet_seq)
                    last_status = now

        except KeyboardInterrupt:
            print("\nInterrompido pelo usuário.")
        finally:
            stop_event.set()
            reader.join(timeout=1.0)

            # Drena o que já chegou à fila antes de encerrar.
            while True:
                try:
                    sample = sample_q.get_nowait()
                except queue.Empty:
                    break

                if (
                    block
                    and (
                        sample["sample_index"] != block[-1]["sample_index"] + 1
                        or sample["source"] != block[-1]["source"]
                    )
                ):
                    if not args.dry_run:
                        try:
                            publicar_bloco(
                                http, args.url, args.node, args.auth,
                                session_id, packet_seq, args.fs, block,
                                args.http_timeout, args.http_retries,
                            )
                            stats.packets_published += 1
                        except requests.RequestException:
                            stats.firebase_errors += 1
                    packet_seq += 1
                    block = []

                block.append(sample)

                if len(block) >= args.block:
                    if not args.dry_run:
                        try:
                            publicar_bloco(
                                http, args.url, args.node, args.auth,
                                session_id, packet_seq, args.fs, block,
                                args.http_timeout, args.http_retries,
                            )
                            stats.packets_published += 1
                        except requests.RequestException:
                            stats.firebase_errors += 1
                    packet_seq += 1
                    block = []

            if block and not args.dry_run:
                try:
                    publicar_bloco(
                        http, args.url, args.node, args.auth,
                        session_id, packet_seq, args.fs, block,
                        args.http_timeout, args.http_retries,
                    )
                    stats.packets_published += 1
                except requests.RequestException:
                    stats.firebase_errors += 1

            print()
            print(
                "Resumo: "
                f"linhas={stats.serial_lines}, "
                f"amostras_validas={stats.valid_samples}, "
                f"JSON_ruim={stats.malformed_lines}, "
                f"gaps={stats.serial_gaps}, "
                f"drop_host={stats.host_queue_drops}, "
                f"pacotes_publicados={stats.packets_published}, "
                f"firebase_erros={stats.firebase_errors}"
            )


if __name__ == "__main__":
    main()
