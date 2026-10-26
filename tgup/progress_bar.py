from tqdm import tqdm

__all__ = ["DownloadProgressBar"]


class DownloadProgressBar(tqdm):
    def __init__(self, *args, **kwargs):
        if "desc" in kwargs and kwargs["desc"] is not None:
            kwargs["desc"] = kwargs["desc"][:32]
        elif len(args) > 1 and args[1] is not None:
            args = (args[0], args[1][:32], *args[2:])
        super().__init__(*args, **kwargs)

    def update_to(self, current, total):
        self.total = total
        self.update(current - self.n)
