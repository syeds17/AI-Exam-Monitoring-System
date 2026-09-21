import time

from src.monitoring.exam_monitor import ExamMonitor


def main():
    print("=" * 60)
    print("       EXAM MONITOR PERFORMANCE PROFILER")
    print("=" * 60)

    monitor = ExamMonitor()

    try:
        session_id = monitor.start()

        print(f"\nSession ID: {session_id}")
        print("Profiling AI processing...")
        print("Keep your face centered and remain mostly still.\n")

        # Let calibration complete first
        calibration_frames = 0

        while calibration_frames < 80:
            state = monitor.process_frame()

            if state is None:
                continue

            calibration_frames += 1

        print("Calibration period complete.")
        print("Now measuring processing performance...\n")

        total_frames = 0
        total_time = 0.0

        test_duration = 10.0
        start_time = time.perf_counter()

        while time.perf_counter() - start_time < test_duration:
            frame_start = time.perf_counter()

            state = monitor.process_frame()

            frame_end = time.perf_counter()

            if state is None:
                continue

            processing_time = frame_end - frame_start

            total_time += processing_time
            total_frames += 1

        elapsed = time.perf_counter() - start_time

        if total_frames > 0:
            avg_processing_time = total_time / total_frames
            processing_fps = total_frames / elapsed
        else:
            avg_processing_time = 0
            processing_fps = 0

        print("=" * 60)
        print("RESULTS")
        print("=" * 60)

        print(f"Frames processed : {total_frames}")
        print(f"Test duration    : {elapsed:.2f} seconds")
        print(f"Average time     : {avg_processing_time * 1000:.2f} ms/frame")
        print(f"Processing FPS   : {processing_fps:.2f}")
        print(f"Capture FPS      : {monitor.camera.get_fps():.2f}")

        print("=" * 60)

    finally:
        monitor.close()

        print("\nExamMonitor closed.")
        print("Profiler complete.")


if __name__ == "__main__":
    main()