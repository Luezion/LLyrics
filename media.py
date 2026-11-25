"""Lê o que está tocando no Windows (System Media Transport Controls).

Funciona com qualquer player que aparece no controle de mídia do Windows:
Spotify, navegadores (YouTube, YouTube Music, SoundCloud...), Apple Music, VLC etc.
Roda numa thread própria e entrega "fotos" do estado via callback.
"""
import asyncio
import datetime as dt
import threading
import time


class Snapshot:
    __slots__ = ("title", "artist", "album", "duration", "position", "playing",
                 "stamp", "app", "thumb", "track_id")

    def __init__(self):
        self.title = ""
        self.artist = ""
        self.album = ""
        self.duration = 0.0
        self.position = 0.0
        self.playing = False
        self.stamp = time.monotonic()
        self.app = ""
        self.thumb = None      # bytes da capa (png/jpg) ou None
        self.track_id = ""


PLAYING = 4  # GlobalSystemMediaTransportControlsSessionPlaybackStatus.PLAYING


class MediaWatcher(threading.Thread):
    def __init__(self, on_update, interval=0.5):
        super().__init__(daemon=True, name="MediaWatcher")
        self.on_update = on_update
        self.interval = interval
        self._halt = threading.Event()
        self.error = None

    def stop(self):
        self._halt.set()

    def run(self):
        try:
            asyncio.run(self._main())
        except Exception as e:  # noqa: BLE001
            self.error = e
            print("[media] parou:", repr(e))

    async def _main(self):
        # Importa aqui para o WinRT inicializar nesta thread (MTA), sem atrapalhar o Qt.
        from winrt.windows.media.control import (
            GlobalSystemMediaTransportControlsSessionManager as Manager,
        )
        manager = await Manager.request_async()
        last_track = None
        last_thumb = None
        while not self._halt.is_set():
            snap = Snapshot()
            try:
                session = self._pick_session(manager)
                if session is not None:
                    await self._fill(session, snap)
                    if snap.track_id != last_track:
                        last_track = snap.track_id
                        last_thumb = await self._thumbnail(session)
                    snap.thumb = last_thumb
                else:
                    last_track = None
            except Exception as e:  # noqa: BLE001
                print("[media] erro lendo sessão:", repr(e))
            self.on_update(snap)
            await asyncio.sleep(self.interval)

    @staticmethod
    def _pick_session(manager):
        try:
            sessions = list(manager.get_sessions())
        except Exception:  # noqa: BLE001
            sessions = []
        for s in sessions:  # prefere quem está tocando
            try:
                if int(s.get_playback_info().playback_status) == PLAYING:
                    return s
            except Exception:  # noqa: BLE001
                pass
        return manager.get_current_session()

    @staticmethod
    async def _fill(session, snap):
        props = await session.try_get_media_properties_async()
        snap.title = (props.title or "").strip()
        snap.artist = (props.artist or props.album_artist or "").strip()
        snap.album = (props.album_title or "").strip()
        snap.app = session.source_app_user_model_id or ""
        info = session.get_playback_info()
        snap.playing = int(info.playback_status) == PLAYING
        tl = session.get_timeline_properties()
        end = _seconds(tl.end_time) - _seconds(tl.start_time)
        pos = _seconds(tl.position)
        snap.duration = max(0.0, end)
        # A posição só é atualizada quando o player avisa; extrapola a partir daí.
        if snap.playing:
            try:
                updated = tl.last_updated_time
                if updated is not None and updated.year > 2000:
                    now = dt.datetime.now(dt.timezone.utc)
                    if updated.tzinfo is None:
                        updated = updated.replace(tzinfo=dt.timezone.utc)
                    elapsed = (now - updated).total_seconds()
                    if 0 <= elapsed < 3600:
                        pos += elapsed
            except Exception:  # noqa: BLE001
                pass
        if snap.duration > 0:
            pos = min(pos, snap.duration)
        snap.position = max(0.0, pos)
        snap.stamp = time.monotonic()
        snap.track_id = f"{snap.app}|{snap.title}|{snap.artist}"

    @staticmethod
    async def _thumbnail(session):
        try:
            props = await session.try_get_media_properties_async()
            ref = props.thumbnail
            if ref is None:
                return None
            from winrt.windows.storage.streams import Buffer, DataReader, InputStreamOptions
            stream = await ref.open_read_async()
            size = int(stream.size)
            if size <= 0 or size > 20_000_000:
                return None
            buf = Buffer(size)
            await stream.read_async(buf, size, InputStreamOptions.READ_AHEAD)
            try:
                return bytes(memoryview(buf))
            except TypeError:
                reader = DataReader.from_buffer(buf)
                data = bytearray(buf.length)
                reader.read_bytes(data)
                return bytes(data)
        except Exception as e:  # noqa: BLE001
            print("[media] sem capa:", repr(e))
            return None


def _seconds(v):
    if v is None:
        return 0.0
    if isinstance(v, dt.timedelta):
        return v.total_seconds()
    try:  # algumas versões devolvem TimeSpan com .duration em unidades de 100ns
        return float(v.duration) / 10_000_000
    except AttributeError:
        return float(v)
