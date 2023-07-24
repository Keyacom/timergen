# timergen
A command-line tool to generate a simple timer.

This also uses a simple DSL for time formatting that includes display widths.
For example, formatting 69420 ms with the format spec `%M:%S.%-2m`
outputs `01:09.42`.

## Prerequisites

- `ffmpeg` is required to compose the video. For now, it must be on `PATH`.

## Command line arguments

```
usage: timergen [-h] [-V] [-v] [-o OUTFILE] [-R] [--keep-session]
                [-f FONT_FAMILY] [-S FONT_SIZE] [-W WIDTH] [-H HEIGHT]
                [-t TEXT_COLOR] [-b BACKGROUND_COLOR] [-F FORMAT_SPEC]
                [-r FRAME_RATE] [-a OUTPUT_FRAME_RATE]
                duration

Generate a simple timer video for a given duration

positional arguments:
  duration              Duration of the timer (in seconds)

options:
  -h, --help, -?        Show this message and exit
  -V, --version         Show this program's version number and exit
  -v, --verbose         Verbose program output (use multiple times to increase verbosity level).
                        The higher the level, the more messages get printed to STDERR.
  -o OUTFILE, --outfile OUTFILE, --output OUTFILE
                        Specify the file name for the output.
                        If not specified, will output to file <session>.mp4, where <session> is a UUIDv4.
  -R, --reversed        Produce reversed output (for countdowns)
  --keep-session        Keep temporary files created during the session

Rendering options:
  Options that handle the output's rendering

  -f FONT_FAMILY, --font-family FONT_FAMILY
                        The font family name. If not specified, a fallback font will be used.
                        Note: It must refer to a TrueType or an OpenType font.
  -S FONT_SIZE, --font-size FONT_SIZE
                        The font size in pixels (default: 40)
  -W WIDTH, --width WIDTH
                        The video width (default: 250)
  -H HEIGHT, --height HEIGHT
                        The video height (default: 50)
  -t TEXT_COLOR, --text TEXT_COLOR, --txcolor TEXT_COLOR
                        The text color  (default: #FFFFFF).
                        Note: If you wish to use a hex code, it may be required to escape the # character.
  -b BACKGROUND_COLOR, --background BACKGROUND_COLOR, --bgcolor BACKGROUND_COLOR
                        The background color (default: #000000)
  -F FORMAT_SPEC, --format FORMAT_SPEC
                        The format specification.
                        
                        One can use the following format codes:
                        - %H: hours (default size: 2)
                        - %M: minutes (default size: 2)
                        - %S: seconds (default size: 2)
                        - %m: milliseconds (default size: -3)
                        - %%: literal %
                        
                        You may also use a digit after the % sign to specify how many last digits should be used
                        (except for %), potentially with a - character to specify how many first digits should be used.
                        
                        Default value: '%M:%S.%-2m' (two minute digits, two second digits, two first millisecond digits)
  -r FRAME_RATE, --frame-rate FRAME_RATE
                        The output frame rate (default: 25)
  -a OUTPUT_FRAME_RATE, --video-frame-rate OUTPUT_FRAME_RATE
                        The video frame rate (if not provided, same as FRAME_RATE)
```
