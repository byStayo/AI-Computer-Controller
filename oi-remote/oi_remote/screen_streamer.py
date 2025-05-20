import asyncio
import io
import mss
from PIL import Image
import os

class ScreenStreamer:
    def __init__(self):
        self.sct = None
        self.quality = int(os.environ.get("OI_STREAM_QUALITY", 75))
        self.fps = int(os.environ.get("OI_STREAM_FPS", 8))
        # Default to a common mobile-friendly resolution, can be overridden
        self.width = int(os.environ.get("OI_STREAM_WIDTH", 800))
        self.height = int(os.environ.get("OI_STREAM_HEIGHT", 450))
        self._is_streaming = False
        self._monitor_selected = 1 # Default to primary monitor

    def _initialize_sct(self):
        if self.sct is None:
            try:
                self.sct = mss.mss()
                if not self.sct.monitors:
                    raise Exception("No monitors found by mss.")
                # Ensure monitor_selected is valid (e.g., 1 for primary, 0 for all, etc.)
                if self._monitor_selected >= len(self.sct.monitors):
                    print(f"Warning: Monitor {self._monitor_selected} not available. Falling back to primary.")
                    self._monitor_selected = 1 # Index 0 is usually all screens, 1 is primary
                if self._monitor_selected < 0:
                     self._monitor_selected = 1 # Ensure positive index if not using 'all screens'

            except Exception as e:
                print(f"Error initializing mss for screen capture: {e}")
                self.sct = None # Ensure it's None if init fails
                raise # Re-raise to signal failure

    async def stream_generator(self):
        if self.sct is None:
            try:
                self._initialize_sct()
            except Exception as e:
                # Yield an error frame or message if sct init fails
                error_message = f"Error initializing screen capture: {e}".encode('utf-8')
                yield (b'--frame\r\n'
                       b'Content-Type: text/plain\r\n\r\n' + error_message + b'\r\n')
                return

        monitor = self.sct.monitors[self._monitor_selected]

        while self._is_streaming:
            try:
                sct_img = self.sct.grab(monitor)
                img = Image.frombytes("RGB", (sct_img.width, sct_img.height), sct_img.rgb, "raw", "BGR")
                
                current_width, current_height = img.size
                aspect_ratio = current_width / current_height

                target_width = self.width
                target_height = self.height

                if current_width / current_height > target_width / target_height:
                    # Wider than target: fit to target_width
                    new_width = target_width
                    new_height = int(target_width / aspect_ratio)
                else:
                    # Taller than target: fit to target_height
                    new_height = target_height
                    new_width = int(target_height * aspect_ratio)
                
                img = img.resize((new_width, new_height), Image.LANCZOS)
                
                buf = io.BytesIO()
                img.save(buf, format="JPEG", quality=self.quality)
                frame = buf.getvalue()
                
                yield (
                    b'--frame\r\n'
                    b'Content-Type: image/jpeg\r\n'
                    b'Content-Length: ' + str(len(frame)).encode() + b'\r\n'
                    b'\r\n' + frame + b'\r\n'
                )
                await asyncio.sleep(1 / self.fps)
            except mss.exception.ScreenShotError as e:
                print(f"Screen capture error (mss.exception.ScreenShotError): {e}. Re-initializing mss.")
                self.sct = None # Force re-initialization
                try:
                    self._initialize_sct()
                    monitor = self.sct.monitors[self._monitor_selected]
                except Exception as init_e:
                    print(f"Failed to re-initialize mss: {init_e}")
                    await asyncio.sleep(5) # Wait before retrying capture
                    continue # Skip this frame
                await asyncio.sleep(1) # Brief pause after re-init before next attempt
            except Exception as e:
                print(f"Screen streaming error: {e}")
                # Consider stopping stream or specific error handling
                await asyncio.sleep(1) # Avoid busy loop on other errors

    def start(self):
        if not self._is_streaming:
            self._is_streaming = True
            print(f"Screen streaming started (FPS: {self.fps}, Quality: {self.quality}, Size: {self.width}x{self.height}).")

    def stop(self):
        if self._is_streaming:
            self._is_streaming = False
            print("Screen streaming stopped.")
            # No need to close sct here if it's to be reused, 
            # but if resources are tight, self.sct.close() could be called.
            # However, mss instances are meant to be fairly persistent.

    @property
    def is_streaming(self):
        return self._is_streaming

# Global instance, to be managed by the FastAPI app lifecycle if possible
# screen_streamer_instance = ScreenStreamer()
