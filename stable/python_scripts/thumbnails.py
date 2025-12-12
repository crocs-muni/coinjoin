import os
import sys
from typing import List, Tuple
from concurrent.futures import ProcessPoolExecutor, as_completed
from PIL import Image
import argparse

IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.webp']


def is_image_file(filename: str) -> bool:
    return any(filename.lower().endswith(ext) for ext in IMAGE_EXTENSIONS)


def resize_image(input_path: str, output_path: str, scale: float = 0.5) -> None:
    """Resize the image by a given scale factor and save to output_path.

    If the input image height is exactly 900, enforce a minimum scale of 0.2
    (preserves behavior from the original script).
    """
    with Image.open(input_path) as img:
        if img.height == 900:
            scale = max(scale, 0.2)
        new_size = (int(img.width * scale), int(img.height * scale))
        # Ensure output directory exists (safe for parallel runs)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        resized_img = img.resize(new_size)
        resized_img.save(output_path)


def collect_image_jobs(src_dir: str, dst_dir: str) -> List[Tuple[str, str]]:
    """Walk src_dir and return a list of (src_path, dst_path) for image files.

    The destination path mirrors the source directory structure under dst_dir.
    """
    jobs: List[Tuple[str, str]] = []
    for root, _dirs, files in os.walk(src_dir):
        rel = os.path.relpath(root, src_dir)
        for fname in files:
            if not is_image_file(fname):
                continue
            src_path = os.path.join(root, fname)
            dst_path = os.path.join(dst_dir, rel, fname)
            jobs.append((src_path, dst_path))
    return jobs


def should_process(src_path: str, dst_path: str, overwrite: bool) -> bool:
    if overwrite:
        return True
    if not os.path.exists(dst_path):
        return True
    try:
        return os.path.getmtime(dst_path) <= os.path.getmtime(src_path)
    except OSError:
        return True


def _worker(args: Tuple[str, str, float, bool]) -> Tuple[str, bool, str]:
    """Worker function to process a single image.

    Returns (dst_path, success, message).
    """
    src_path, dst_path, scale, overwrite = args
    try:
        if not should_process(src_path, dst_path, overwrite):
            return (dst_path, True, 'skipped (already resized)')
        resize_image(src_path, dst_path, scale)
        return (dst_path, True, 'resized')
    except Exception as e:
        return (dst_path, False, f'failed: {e}')


def copy_and_resize_images_parallel(src_dir: str, dst_dir: str, scale: float = 0.15,
                                    overwrite: bool = False, max_workers: int = 10) -> None:
    """Collect all image files first, then process them in parallel using CPU workers."""
    # 1) Collect all jobs first
    jobs = collect_image_jobs(src_dir, dst_dir)
    if not jobs:
        print('No image files found. Nothing to do.')
        return

    # 2) Create base destination folder to mirror structure as needed
    os.makedirs(dst_dir, exist_ok=True)

    # 3) Process in parallel
    total = len(jobs)
    print(f'Found {total} image(s). Processing with {max_workers} workers...')

    # Bundle arguments to avoid large closures in multiprocessing
    task_args = [(src, dst, scale, overwrite) for (src, dst) in jobs]

    completed = 0
    succeeded = 0
    skipped = 0

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_worker, a): a for a in task_args}
        for fut in as_completed(futures):
            dst_path, ok, msg = fut.result()
            completed += 1
            if ok and msg.startswith('skipped'):
                skipped += 1
            elif ok:
                succeeded += 1
            print(f'[{completed}/{total}] {msg}: {dst_path}')

    print(f'Done. Succeeded: {succeeded}, Skipped: {skipped}, Total: {total}.')


def parse_args(argv: List[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Resize images from SRC to DST (parallel).')
    p.add_argument('src', help='Source directory to scan for images')
    p.add_argument('dst', help='Destination directory (mirrors SRC structure)')
    p.add_argument('--scale', type=float, default=0.15,
                   help='Scale factor (default: 0.15)')
    p.add_argument('--overwrite', action='store_true',
                   help='Overwrite existing files regardless of timestamps')
    p.add_argument('--workers', type=int, default=10,
                   help='Number of parallel workers (default: 10)')
    return p.parse_args(argv)


if __name__ == '__main__':
    args = parse_args(sys.argv[1:])
    copy_and_resize_images_parallel(
        src_dir=args.src,
        dst_dir=args.dst,
        scale=args.scale,
        overwrite=args.overwrite,
        max_workers=args.workers,
    )
