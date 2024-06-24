# SPDX-FileCopyrightText: 2024 Michał Pokusa
#
# SPDX-License-Identifier: Unlicense

try:
    from typing import Any, Dict, Generator, Tuple, Union
except ImportError:
    pass

from random import choice
from time import sleep

import socketpool
import wifi

from adafruit_httpserver import OK_200, Headers, Request, Response, Server, Status

pool = socketpool.SocketPool(wifi.radio)
server = Server(pool, "/static", debug=True)


class XMixedReplaceResponse(Response):

    def __init__(
        self,
        request: Request,
        body: Generator[Union[str, bytes], Any, Any],
        frame_content_type: str,
        *,
        status: Union[Status, Tuple[int, str]] = OK_200,
        headers: Union[Headers, Dict[str, str]] = None,
        cookies: Dict[str, str] = None,
        content_type: str = None,
    ) -> None:
        super().__init__(
            request=request,
            headers=headers,
            cookies=cookies,
            status=status,
            content_type=content_type,
        )
        self._boundary = self._get_random_boundary()
        self._frame_content_type = frame_content_type
        self._headers.setdefault(
            "Content-Type", f"multipart/x-mixed-replace; boundary={self._boundary}"
        )
        self._body = body

    @staticmethod
    def _get_random_boundary() -> str:
        symbols = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        return "--" + "".join([choice(symbols) for _ in range(16)])

    def _send_frame(self, frame: Union[str, bytes] = "") -> None:
        encoded_frame = frame.encode("utf-8") if isinstance(frame, str) else frame

        self._send_bytes(
            self._request.connection, bytes(f"{self._boundary}\r\n", "utf-8")
        )
        self._send_bytes(
            self._request.connection,
            bytes(f"Content-Type: {self._frame_content_type}\r\n\r\n", "utf-8"),
        )
        self._send_bytes(self._request.connection, bytes(encoded_frame) + b"\r\n")

    def _send(self) -> None:
        self._send_headers()

        for frame in self._body():
            if 0 < len(frame):  # Don't send empty chunks
                self._send_frame(frame)

        self._close_connection()


@server.route("/live-feed")
def live_feed_handler(request: Request):
    def body_generator():
        while True:
            for i in range(1, 5):
                with open(f"frames/frame{i}.jpg", "rb") as frame_file:
                    content = frame_file.read()

                yield content
                print(f"Frame {i} sent.")
                sleep(0.5)

    return XMixedReplaceResponse(
        request,
        body_generator,
        frame_content_type="image/jpeg",
        content_type="video/mp4",
    )


server.serve_forever()
