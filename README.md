# tgup

![PyPI - Python Version](https://img.shields.io/pypi/pyversions/tgup?link=https%3A%2F%2Fpypi.org%2Fproject%2Ftgup%2F)
![PyPI - Status](https://img.shields.io/pypi/status/tgup?link=https%3A%2F%2Fpypi.org%2Fproject%2Ftgup%2F)
![PyPI - Version](https://img.shields.io/pypi/v/tgup?link=https%3A%2F%2Fpypi.org%2Fproject%2Ftgup%2F)

Upload files to Telegram using your account.

This project is partially based on [telegram-upload](https://github.com/Nekmo/telegram-upload) by [Nekmo](https://github.com/Nekmo),
it was recreated because the original project seems abandoned.

[PyPI page](https://pypi.org/project/tgup/)

## Installation

With pipx (**preferred method**):
```bash
pipx install tgup
```

With pip:
```bash
pip install tgup
```

## Usage

To send files:
```bash
tgup dir1/ file1 dir2/abc/
```
It will send the files to your personal chat.

To see all the options, run: `tgup --help`

## Acknowledgements

- Based on [telegram-upload](https://github.com/Nekmo/telegram-upload)
