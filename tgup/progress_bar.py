from tqdm import tqdm

__all__ = ["DownloadProgressBar"]


class DownloadProgressBar(tqdm):
    def update_to(self, current, total):
        self.total = total
        self.update(current - self.n)
