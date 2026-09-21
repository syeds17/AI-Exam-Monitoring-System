import cv2
import time

from src.camera.threaded_camera import ThreadedCamera


def main():
    print("=" * 50)
    print("       THREADED CAMERA TEST")
    print("=" * 50)

    camera = ThreadedCamera(
        camera_index=0,
        width=1280,
        height=720,
        target_fps=30,
    )

    try:
        print("\nStarting camera...")

        camera.start()

        print("Camera started.")
        print("Press Q to stop.\n")

        start_time = time.perf_counter()
        last_print = start_time

        while True:
            frame = camera.read()

            if frame is None:
                continue

            cv2.putText(
                frame,
                f"Capture FPS: {camera.get_fps():.1f}",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 255, 0),
                2,
            )

            cv2.imshow("Threaded Camera Test", frame)

            now = time.perf_counter()

            if now - last_print >= 2:
                print(
                    f"Capture FPS: {camera.get_fps():.1f} | "
                    f"Frames: {camera.frame_count}"
                )
                last_print = now

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    finally:
        camera.stop()
        cv2.destroyAllWindows()

        elapsed = time.perf_counter() - start_time

        print("\nCamera stopped.")
        print(f"Total frames captured: {camera.frame_count}")
        print(f"Test duration: {elapsed:.2f} seconds")
        print("\n✅ Threaded camera test complete.")


if __name__ == "__main__":
    main()