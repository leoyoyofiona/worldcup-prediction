import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import httpx

from .cache import now_iso, read_raw, save_raw
from .config import LOCAL_WORLDCUP_MATCHES_PATHS, REQUEST_TIMEOUT_SECONDS


@dataclass(frozen=True)
class WebSource:
    id: str
    name: str
    url: str
    filename: str
    required: bool = False


WEB_SOURCES: List[WebSource] = [
    WebSource(
        id="schedule_openfootball",
        name="openfootball 2026 世界杯赛程",
        url="https://raw.githubusercontent.com/openfootball/worldcup.json/master/2026/worldcup.json",
        filename="schedule_openfootball.json",
        required=True,
    ),
    WebSource(
        id="results_history",
        name="国际国家队历史比赛 CSV",
        url="https://raw.githubusercontent.com/martj42/international_results/master/results.csv",
        filename="international_results.csv",
        required=True,
    ),
    WebSource(
        id="fifa_ranking",
        name="FIFA 男足世界排名页面",
        url="https://inside.fifa.com/fifa-world-ranking/men",
        filename="fifa_ranking.html",
    ),
    WebSource(
        id="yiwu_index",
        name="小商品指数网",
        url="https://www.ywindex.com/",
        filename="yiwu_index.html",
    ),
    WebSource(
        id="mofcom_forecast",
        name="商务预报",
        url="https://cif.mofcom.gov.cn/cif/",
        filename="mofcom_forecast.html",
    ),
    WebSource(
        id="chinagoods",
        name="中国商品网",
        url="https://www.chinagoods.com/",
        filename="chinagoods.html",
    ),
    WebSource(
        id="yiwu_worldcup_search",
        name="义乌世界杯订单公开搜索页",
        url="https://duckduckgo.com/html/?q=%E4%B9%89%E4%B9%8C%20%E4%B8%96%E7%95%8C%E6%9D%AF%20%E8%AE%A2%E5%8D%95%20%E5%9B%BD%E5%AE%B6%E9%98%9F%20%E7%90%83%E8%A1%A3%20%E5%9B%BD%E6%97%97",
        filename="yiwu_worldcup_search.html",
    ),
    WebSource(
        id="oddsjet_europe",
        name="欧洲盘口 OddsJet IE 世界杯冠军赔率",
        url="https://www.oddsjet.com/en-ie/fifa/world-cup/outright-winner/odds",
        filename="oddsjet_europe.html",
    ),
    WebSource(
        id="oddsjet_asia",
        name="亚洲盘口 OddsJet IN 世界杯冠军赔率",
        url="https://www.oddsjet.com/en-in/fifa/world-cup/outright-winner/odds",
        filename="oddsjet_asia.html",
    ),
    WebSource(
        id="oddsjet_oceania",
        name="大洋洲盘口 OddsJet AU 世界杯冠军赔率",
        url="https://www.oddsjet.com/en-au/fifa/world-cup/outright-winner/odds",
        filename="oddsjet_oceania.html",
    ),
    WebSource(
        id="oddsjet_africa",
        name="非洲盘口 OddsJet ZA 世界杯冠军赔率",
        url="https://www.oddsjet.com/en-za/fifa/world-cup/outright-winner/odds",
        filename="oddsjet_africa.html",
    ),
    WebSource(
        id="oddsjet_north_america",
        name="北美盘口 OddsJet CA 世界杯冠军赔率",
        url="https://www.oddsjet.com/en-ca/fifa/world-cup/outright-winner/odds",
        filename="oddsjet_north_america.html",
    ),
    WebSource(
        id="oddsjet_south_america",
        name="南美盘口 OddsJet BR 世界杯冠军赔率",
        url="https://www.oddsjet.com/en-br/fifa/world-cup/outright-winner/odds",
        filename="oddsjet_south_america.html",
    ),
    WebSource(
        id="comparebet_uk",
        name="英国盘口 Compare.bet 世界杯冠军赔率",
        url="https://www.compare.bet/betting/football/world-cup/winner-odds",
        filename="comparebet_uk.html",
    ),
    WebSource(
        id="lineup_injury_search",
        name="公开首发/伤病/停赛搜索页",
        url="https://duckduckgo.com/html/?q=2026%20World%20Cup%20lineup%20injury%20suspension%20starting%20XI",
        filename="lineup_injury_search.html",
    ),
    WebSource(
        id="referee_weather_search",
        name="公开裁判/天气信息搜索页",
        url="https://duckduckgo.com/html/?q=2026%20World%20Cup%20referee%20weather%20stadium%20forecast",
        filename="referee_weather_search.html",
    ),
]

AUTHORIZED_DATA_SOURCES: List[WebSource] = [
    WebSource(
        id="sportradar_authorized",
        name="Sportradar 授权赛事/球员/赔率数据",
        url="https://developer.sportradar.com/",
        filename="sportradar_authorized.json",
    ),
    WebSource(
        id="genius_sports_authorized",
        name="Genius Sports 授权赛事/赔率数据",
        url="https://www.geniussports.com/",
        filename="genius_sports_authorized.json",
    ),
]

LOCAL_WORLDCUP_SOURCE = WebSource(
    id="worldcup_matches_local",
    name="本地历届世界杯比赛 CSV",
    url="file:///Users/leo/Downloads/世界杯数据/WorldCupMatches.csv",
    filename="worldcup_matches_local.csv",
)


def source_status(
    source: WebSource,
    ok: bool,
    message: str,
    byte_count: int = 0,
    using_cache: bool = False,
) -> Dict[str, object]:
    return {
        "id": source.id,
        "name": source.name,
        "url": source.url,
        "required": source.required,
        "ok": ok,
        "status": "ok" if ok else "error",
        "message": message,
        "bytes": byte_count,
        "using_cache": using_cache,
        "fetched_at": now_iso(),
    }


def authorized_source_statuses() -> List[Dict[str, object]]:
    return [
        source_status(
            source,
            False,
            "需要商业授权/API Key；当前版本不伪造数据，未授权时自动跳过。",
        )
        for source in AUTHORIZED_DATA_SOURCES
    ]


def read_text_with_fallback(path: Path) -> str:
    for encoding in ("utf-8-sig", "utf-8", "latin-1", "cp1252"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="latin-1", errors="replace")


def local_worldcup_source_status(path: Optional[Path], ok: bool, message: str, byte_count: int = 0, using_cache: bool = False) -> Dict[str, object]:
    source = LOCAL_WORLDCUP_SOURCE
    if path is not None:
        source = WebSource(
            id=LOCAL_WORLDCUP_SOURCE.id,
            name=LOCAL_WORLDCUP_SOURCE.name,
            url=path.as_uri(),
            filename=LOCAL_WORLDCUP_SOURCE.filename,
        )
    return source_status(source, ok, message, byte_count, using_cache)


def load_local_worldcup_source() -> Tuple[Optional[str], Dict[str, object]]:
    errors: List[str] = []
    for path in LOCAL_WORLDCUP_MATCHES_PATHS:
        if not path.exists():
            continue
        try:
            content = read_text_with_fallback(path)
        except OSError as exc:
            errors.append(f"{path}: {exc}")
            continue
        save_raw(LOCAL_WORLDCUP_SOURCE.filename, content)
        return content, local_worldcup_source_status(path, True, "已读取本地 CSV", len(content.encode("utf-8")))

    cached = read_raw(LOCAL_WORLDCUP_SOURCE.filename)
    if cached is not None:
        return cached, local_worldcup_source_status(None, True, "原始 CSV 不可用，已使用本地缓存", len(cached.encode("utf-8")), True)

    message = "没有找到本地 WorldCupMatches.csv"
    if errors:
        message += "；" + "；".join(errors[:2])
    return None, local_worldcup_source_status(None, False, message)


async def _fetch_one(client: httpx.AsyncClient, source: WebSource) -> Tuple[WebSource, Optional[str], Dict[str, object]]:
    try:
        response = await asyncio.wait_for(client.get(source.url), timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
    except asyncio.TimeoutError:
        return source, None, source_status(source, False, f"抓取超时（{REQUEST_TIMEOUT_SECONDS:.0f} 秒）")
    except Exception as exc:
        return source, None, source_status(source, False, str(exc))
    text = response.text
    return source, text, source_status(source, True, "已抓取", len(text.encode("utf-8")))


async def fetch_sources() -> Tuple[Dict[str, str], List[Dict[str, object]]]:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125 Safari/537.36"
        )
    }
    timeout = httpx.Timeout(REQUEST_TIMEOUT_SECONDS, connect=REQUEST_TIMEOUT_SECONDS)
    async with httpx.AsyncClient(
        headers=headers,
        timeout=timeout,
        follow_redirects=True,
    ) as client:
        tasks = [_fetch_one(client, source) for source in WEB_SOURCES]
        fetched = await asyncio.gather(*tasks)

    raw_payloads: Dict[str, str] = {}
    statuses: List[Dict[str, object]] = []
    for source, content, status in fetched:
        if content is not None:
            save_raw(source.filename, content)
            raw_payloads[source.id] = content
            statuses.append(status)
            continue

        cached = read_raw(source.filename)
        if cached is not None:
            raw_payloads[source.id] = cached
            statuses.append(
                source_status(
                    source,
                    True,
                    "在线抓取失败，已使用本地缓存",
                    len(cached.encode("utf-8")),
                    using_cache=True,
                )
            )
        else:
            statuses.append(status)
    local_content, local_status = load_local_worldcup_source()
    if local_content is not None:
        raw_payloads[LOCAL_WORLDCUP_SOURCE.id] = local_content
    statuses.append(local_status)
    statuses.extend(authorized_source_statuses())
    return raw_payloads, statuses


def load_cached_sources() -> Tuple[Dict[str, str], List[Dict[str, object]]]:
    raw_payloads: Dict[str, str] = {}
    statuses: List[Dict[str, object]] = []
    for source in WEB_SOURCES:
        cached = read_raw(source.filename)
        if cached is None:
            statuses.append(source_status(source, False, "没有本地缓存"))
            continue
        raw_payloads[source.id] = cached
        statuses.append(
            source_status(
                source,
                True,
                "已读取本地缓存",
                len(cached.encode("utf-8")),
                using_cache=True,
            )
        )
    local_content, local_status = load_local_worldcup_source()
    if local_content is not None:
        raw_payloads[LOCAL_WORLDCUP_SOURCE.id] = local_content
    statuses.append(local_status)
    statuses.extend(authorized_source_statuses())
    return raw_payloads, statuses
