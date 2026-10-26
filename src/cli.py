"""Command-line interface for VoiceForge server, benchmarks, and VAD evaluation."""

import time
from pathlib import Path
from typing import Optional
import numpy as np
import typer
import uvicorn
from rich.console import Console
from rich.table import Table

from .config import settings
from .vad.silero import SileroVAD

app = typer.Typer(help="VoiceForge: Open-source real-time voice agent server")
console = Console()


@app.command()
def serve(
    host: str = typer.Option(settings.host, "--host", "-h", help="Host address to bind"),
    port: int = typer.Option(settings.port, "--port", "-p", help="Port number to listen on"),
    reload: bool = typer.Option(False, "--reload", "-r", help="Enable live code reloading")
):
    """Start the VoiceForge FastAPI and WebRTC signaling server."""
    console.print(f"[bold green]Starting VoiceForge Server on http://{host}:{port}[/bold green]")
    console.print(f"Default STT: [cyan]{settings.default_stt_provider}[/cyan]")
    console.print(f"Default LLM: [cyan]{settings.default_llm_provider}[/cyan]")
    console.print(f"Default TTS: [cyan]{settings.default_tts_provider}[/cyan]")
    console.print(f"Silero VAD Model: [yellow]{settings.vad_model_path}[/yellow]")

    uvicorn.run("src.server.app:app", host=host, port=port, reload=reload)


@app.command()
def benchmark(
    frames: int = typer.Option(500, "--frames", "-f", help="Number of 32ms audio frames to evaluate")
):
    """Benchmark Silero VAD v5 ONNX CPU execution latency and memory overhead."""
    console.print(f"[bold cyan]Running Silero VAD v5 benchmark across {frames} frames...[/bold cyan]")

    vad = SileroVAD(settings.vad_model_path)
    durations = []

    # Generate synthetic 512-sample audio frames
    dummy_frame = np.random.uniform(-0.5, 0.5, 512).astype(np.float32)

    # Warmup
    for _ in range(20):
        vad.process_chunk(dummy_frame)

    for _ in range(frames):
        t0 = time.perf_counter()
        vad.process_chunk(dummy_frame)
        durations.append((time.perf_counter() - t0) * 1000.0)

    durations = np.array(durations)
    avg_ms = float(np.mean(durations))
    p50_ms = float(np.percentile(durations, 50))
    p90_ms = float(np.percentile(durations, 90))
    p99_ms = float(np.percentile(durations, 99))
    min_ms = float(np.min(durations))
    max_ms = float(np.max(durations))

    table = Table(title="Silero VAD v5 ONNX CPU Benchmark Results")
    table.add_column("Metric", style="cyan")
    table.add_column("Latency (ms)", style="green", justify="right")
    table.add_column("Real-Time Factor", style="yellow", justify="right")

    # 32ms is the frame length
    table.add_row("Mean Latency", f"{avg_ms:.2f} ms", f"{32.0 / avg_ms:.1f}x real-time")
    table.add_row("P50 (Median)", f"{p50_ms:.2f} ms", f"{32.0 / p50_ms:.1f}x real-time")
    table.add_row("P90", f"{p90_ms:.2f} ms", f"{32.0 / p90_ms:.1f}x real-time")
    table.add_row("P99", f"{p99_ms:.2f} ms", f"{32.0 / p99_ms:.1f}x real-time")
    table.add_row("Min", f"{min_ms:.2f} ms", "-")
    table.add_row("Max", f"{max_ms:.2f} ms", "-")

    console.print(table)
    if avg_ms < 3.0:
        console.print("[bold green]Benchmark passed: CPU inference latency is sub-3ms.[/bold green]")


@app.command()
def test_vad(
    wav_path: Path = typer.Argument(..., help="Path to 16kHz mono WAV audio file"),
    threshold: float = typer.Option(0.5, "--threshold", "-t", help="VAD detection threshold")
):
    """Test voice activity detection on a local WAV audio recording."""
    import soundfile as sf
    from .vad.detector import VADDetector

    if not wav_path.exists():
        console.print(f"[bold red]File not found: {wav_path}[/bold red]")
        raise typer.Exit(code=1)

    data, sr = sf.read(str(wav_path), dtype="int16")
    if sr != 16000:
        console.print(f"[yellow]Resampling from {sr}Hz to 16,000Hz...[/yellow]")
        num_target = int(len(data) * 16000 / sr)
        indices = np.linspace(0, len(data) - 1, num_target)
        data = np.interp(indices, np.arange(len(data)), data).astype(np.int16)

    vad = SileroVAD(settings.vad_model_path)
    segments = []
    current_start = None

    def on_start():
        nonlocal current_start
        current_start = time.time()

    def on_end(bytes_data):
        segments.append(len(bytes_data))

    detector = VADDetector(
        vad=vad,
        threshold=threshold,
        on_speech_start=on_start,
        on_speech_end=on_end
    )

    detector.process_pcm_bytes(data.tobytes())
    console.print(f"[green]Detected {len(segments)} distinct speech segments in audio file.[/green]")


if __name__ == "__main__":
    app()
