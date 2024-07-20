# SPDX-FileCopyrightText: 2024 Michał Pokusa
#
# SPDX-License-Identifier: Unlicense

try:
    from typing import Dict, List, Tuple, Union
except ImportError:
    pass

from asyncio import create_task, gather, run
from asyncio import sleep as async_sleep
from random import choice

import socketpool
import wifi

from adafruit_httpserver import Server, Request, Response, Headers, Status, OK_200


pool = socketpool.SocketPool(wifi.radio)
server = Server(pool, "/static", debug=True)


class XMixedReplaceResponse(Response):

    def __init__(
        self,
        request: Request,
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
        self._headers.setdefault(
            "Content-Type", f"multipart/x-mixed-replace; boundary={self._boundary}"
        )
        self._frame_content_type = frame_content_type

    @staticmethod
    def _get_random_boundary() -> str:
        symbols = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        return "--" + "".join([choice(symbols) for _ in range(16)])

    def send_frame(self, frame: Union[str, bytes] = "") -> None:
        encoded_frame = bytes(
            frame.encode("utf-8") if isinstance(frame, str) else frame
        )

        self._send_bytes(
            self._request.connection, bytes(f"{self._boundary}\r\n", "utf-8")
        )
        self._send_bytes(
            self._request.connection,
            bytes(f"Content-Type: {self._frame_content_type}\r\n\r\n", "utf-8"),
        )
        self._send_bytes(self._request.connection, encoded_frame)
        self._send_bytes(self._request.connection, bytes("\r\n", "utf-8"))

    def _send(self) -> None:
        self._send_headers()

    def close(self) -> None:
        self._close_connection()


live_video_connection: List[XMixedReplaceResponse] = []


@server.route("/live-feed")
def live_feed_handler(request: Request):

    response = XMixedReplaceResponse(request, frame_content_type="image/jpeg")
    live_video_connection.append(response)

    return response


def get_frame() -> bytes:
    # There goes the code that gets the frame from the camera
    ...


async def handle_send_live_video_frames():
    while True:
        await async_sleep(0.25)

        frame = get_frame()

        for connection in live_video_connection:
            try:
                connection.send_frame(frame)
            except BrokenPipeError:
                connection.close()
                live_video_connection.remove(connection)


async def handle_http_requests():
    server.start(str(wifi.radio.ipv4_address))

    while True:
        await async_sleep(0)

        server.poll()


async def main():
    await gather(
        create_task(handle_send_live_video_frames()),
        create_task(handle_http_requests()),
    )


run(main())
