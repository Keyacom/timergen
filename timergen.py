from argparse import ArgumentParser, RawTextHelpFormatter
from functools import lru_cache
from itertools import accumulate, islice, count
from os import environ
from pathlib import Path
import re
from shutil import copy, rmtree, which
from subprocess import run as run_system_command
from sys import exit, stderr as STDERR
from textwrap import dedent
from typing import Any
from uuid import uuid4

from PIL import Image, ImageDraw
from PIL.ImageColor import getrgb as get_rgb_tuple
from PIL.ImageFont import (
    truetype as get_truetype_font,
    load_default as load_default_font,
    ImageFont,
    FreeTypeFont,
)

VERSION = "0.1"


class TimergenConfig:
    duration: float
    text_color: tuple[int, int, int] | tuple[int, int, int, int]
    background: tuple[int, int, int] | tuple[int, int, int, int]
    outfile: str
    frame_rate: int
    output_frame_rate: int
    time_format: str
    verbosity: int
    keep_session: bool
    width: int
    height: int
    font_family: str | None
    font: ImageFont | FreeTypeFont
    font_size: int
    reverse: bool


@lru_cache(1)
def get_argument_parser() -> ArgumentParser:
    DEFAULT_FMT = " (default: %(default)s)"
    parser = ArgumentParser(
        prog="timergen",
        description="Generate a simple timer video for a given duration",
        epilog=dedent(
            """\
            Author: https://github.com/Keyacom
            Repository: https://github.com/Keyacom/timergen
            Released under the MIT license
            """
        ),
        formatter_class=RawTextHelpFormatter,
        add_help=False,  # will define help commands later
    )
    parser.add_argument(
        "-h", "--help", "-?", action="help", help="Show this message and exit"
    )
    parser.add_argument(
        "-V",
        "--version",
        action="version",
        version=f"%(prog)s {VERSION}",
        help="Show this program's version number and exit",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        dest="verbosity",
        default=0,
        help=dedent(
            """\
        Verbose program output (use multiple times to increase verbosity level).
        The higher the level, the more messages get printed to STDERR.
        """
        ),
    )
    parser.add_argument(
        "duration",
        type=float,
        help="Duration of the timer (in seconds)",
    )
    parser.add_argument(
        "-o",
        "--outfile",
        "--output",
        help=dedent(
            f"""\
            Specify the file name for the output.
            If not specified, will output to file <session>.mp4, where <session> is a UUIDv4.
            """,
        ),
    )
    parser.add_argument(
        "-R",
        "--reversed",
        dest="reverse",
        action="store_true",
        help="Produce reversed output (for countdowns)",
    )
    parser.add_argument(
        "--keep-session",
        dest="keep_session",
        action="store_true",
        help="Keep temporary files created during the session",
    )
    render_optgroup = parser.add_argument_group(
        title="Rendering options",
        description="Options that handle the output's rendering",
    )
    render_optgroup.add_argument(
        "-f",
        "--font-family",
        help=dedent(
            f"""\
            The font family name. If not specified, a fallback font will be used.
            Note: It must refer to a TrueType or an OpenType font.
            """
        ),
    )
    render_optgroup.add_argument(
        "-S",
        "--font-size",
        help="The font size in pixels" + DEFAULT_FMT,
        default=40,
    )
    render_optgroup.add_argument(
        "-W",
        "--width",
        help="The video width" + DEFAULT_FMT,
        type=int,
        default=250,
    )
    render_optgroup.add_argument(
        "-H",
        "--height",
        help="The video height" + DEFAULT_FMT,
        type=int,
        default=50,
    )
    render_optgroup.add_argument(
        "-t",
        "--text",
        "--txcolor",
        default=(255, 255, 255),  # white
        dest="text_color",
        type=get_rgb_tuple,
        metavar="TEXT_COLOR",
        help=dedent(
            f"""\
            The text color {DEFAULT_FMT % {'default': '#FFFFFF'}}.
            Note: If you wish to use a hex code, it may be required to escape the # character.
        """
        ),
    )
    render_optgroup.add_argument(
        "-b",
        "--background",
        "--bgcolor",
        default=(0, 0, 0),  # black
        dest="background",
        type=get_rgb_tuple,
        metavar="BACKGROUND_COLOR",
        help="The background color" + DEFAULT_FMT % {"default": "#000000"},
    )
    render_optgroup.add_argument(
        "-F",
        "--format",
        default="%M:%S.%-2m",
        metavar="FORMAT_SPEC",
        dest="time_format",
        help=dedent(
            f"""\
            The format specification.

            One can use the following format codes:
            - %%H: hours (default size: 2)
            - %%M: minutes (default size: 2)
            - %%S: seconds (default size: 2)
            - %%m: milliseconds (default size: -3)
            - %%%%: literal %%

            You may also use a digit after the %% sign to specify how many last digits should be used
            (except for %%), potentially with a - character to specify how many first digits should be used.

            Default value: '%%M:%%S.%%-2m' (two minute digits, two second digits, two first millisecond digits)
            """
        ),
    )
    render_optgroup.add_argument(
        "-r",
        "--frame-rate",
        default=25,
        type=int,
        help="The output frame rate" + DEFAULT_FMT,
    )
    render_optgroup.add_argument(
        "-a",
        "--video-frame-rate",
        dest="output_frame_rate",
        type=int,
        help="The video frame rate (if not provided, same as FRAME_RATE)",
    )
    return parser


def get_units_from_seconds(seconds: int, /) -> tuple[int, int, int, int]:
    return get_units_from_milliseconds(seconds * 1000)


def get_units_from_milliseconds(milliseconds: int, /) -> tuple[int, int, int, int]:
    secs, millis = divmod(milliseconds, 1000)
    mins, secs = divmod(secs, 60)
    hours, mins = divmod(mins, 60)
    return (hours, mins, secs, millis)


def message(msg: Any, min: int, v: int, /):
    if v >= min:
        print(msg, file=STDERR)


def create_message_funcs(verbosity):
    return [(lambda msg: message(msg, i, verbosity)) for i in range(4)]


def format_time(millis: int, fmt: str, /):
    hr, min, sec, ms = get_units_from_milliseconds(millis)
    rx = re.compile(
        r"""
        % # must start with the '%' character
        (?P<spec>
            (?P<digits>-?\d+)? # optional number of digits
            (?P<unit>[HMSm]) # unit to use
        |%) # ...or a '%' character for the whole spec to literally mean a '%' sign
        """,
        re.X,
    )

    def replacer(ma: re.Match[str]) -> str:
        if ma["spec"] == "%":
            return "%%"
        dig = ma["digits"]
        u = ma["unit"]
        default_digs = {"H": -2, "M": -2, "S": -2, "m": 3}
        if dig is None:
            dig = default_digs[u]
        else:
            dig = -int(dig)
        if dig == 0:
            raise ValueError("width cannot be 0")
        if dig < 0:
            s = slice(dig, None)
        else:
            s = slice(None, dig)
        return str({"H": hr, "M": min, "S": sec, "m": ms}[u]).rjust(
            max(abs(dig), default_digs[u]), "0"
        )[s]

    return (
        rx.sub(replacer, fmt) % ()
    )  # This makes sure there are no unwanted format specs


def millis_counts(fps: int, /):
    yield from accumulate([0] + [1000 // fps] * (fps - 1))


def frame_counts(fps: int, /):
    yield from islice(count(), fps)


def generate_frames(config: TimergenConfig, path: Path):
    *_, dm2, dm3 = create_message_funcs(config.verbosity)

    frames = config.duration * config.frame_rate
    times = []
    # TODO: implement formatting with frame count instead of milliseconds
    for i in range(int(config.duration)):
        for j in millis_counts(config.frame_rate):
            times.append(format_time(i * 1000 + j, config.time_format))
    # times for the last, partial second
    for i in millis_counts(config.frame_rate):
        if i < config.duration % 1 * 1000:
            times.append(
                format_time(int(config.duration + 1) * 1000 + i, config.time_format)
            )

    for i, tx in enumerate(times):
        with Image.new("RGBA", (config.width, config.height), config.background) as img:
            dm2(f"Created image #{i}")
            draw = ImageDraw.Draw(img)
            dm3(f"Created draw handle for image #{i}")
            draw.text(
                (config.width / 2, config.height / 2),
                tx,
                fill=config.text_color,
                font=config.font,
                anchor="mm",
            )
            dm3(f"Drew text {tx!r} on image #{i}")
            ipath = path / f"{i}.png"
            img.save(ipath)
            dm2(f"Saved image #{i} to {ipath}")


def main() -> int:
    config = get_argument_parser().parse_args(namespace=TimergenConfig())
    if config.font_family is None:
        config.font = load_default_font()
    else:
        config.font = get_truetype_font(
            config.font_family, config.font_size  # , encoding="utf8"
        )
    if config.output_frame_rate is None:
        config.output_frame_rate = config.frame_rate
    #print(vars(config))
    # short for "diagnostic message x"
    dm0, dm1, dm2, dm3 = create_message_funcs(config.verbosity)
    # print(format_time(int(config.duration * 1000), config.format))
    if which("ffmpeg") is None:
        dm0(f'ERROR: ffmpeg not on $PATH\nThe current $PATH is:\n{environ["PATH"]}')
        return 1
    # In the name of the temporary directory (and file if the file name is not specified)
    session = uuid4()
    if config.outfile is None:
        config.outfile = f"{session}.mp4"
    path = Path(f"timergen-{session}")
    path.mkdir(exist_ok=True)
    dm1(f"Created directory {path}")
    generate_frames(config, path)
    tmp_result_path = str(path / "result.mp4")
    ffmpeg_args = [
        "ffmpeg",
        "-framerate",
        str(config.frame_rate),  # frame rate (input)
        "-i",
        str(path / "%d.png"),  # input files
        "-c:v",
        "libx264",  # codec
        "-pix_fmt",
        "yuv420p",  # codec setting: pixel format
        "-r",
        str(config.output_frame_rate),  # frame rate (output)
        tmp_result_path,
    ]
    run_system_command(ffmpeg_args)
    if config.reverse:
        run_system_command(
            [
                "ffmpeg",
                "-i",
                tmp_result_path,
                "-vf",
                "reverse",
                config.outfile,  # output file name
            ]
        )
    else:
        copy(tmp_result_path, config.outfile)
    if config.keep_session:
        dm1(f"Directory {path} was KEPT.")
    else:
        rmtree(path)
        dm1(f"Deleted directory {path}")
    return 0


if __name__ == "__main__":
    exit(main())
