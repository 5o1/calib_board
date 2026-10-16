"""Calibrate pinhole camera intrinsics from multiple ChArUco photographs."""
import argparse
from pathlib import Path

import cv2
import numpy as np

from .common import DEFAULT_SPEC, image_paths, make_board, read_data, save_data


def calibrate(images, spec, min_views=10, overlay_dir=None):
    """Detect without prior K/D, then fit the standard five-coefficient model.

    Unreadable images and mixed resolutions are errors. Images with fewer than
    six non-collinear corners are reported as skipped, never silently removed.
    No points or views are rejected based on their fitted reprojection error.
    """
    if min_views < 3:
        raise ValueError('At least three views are required; use ten or more in practice')
    board, _ = make_board(spec)
    params = cv2.aruco.CharucoParameters()
    params.minMarkers = 2
    params.tryRefineMarkers = False
    detector_params = cv2.aruco.DetectorParameters()
    detector_params.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_NONE
    detector = cv2.aruco.CharucoDetector(board, params, detector_params)
    objects, pixels, views, skipped = [], [], [], []
    size = None
    for index, path in enumerate(images):
        image = cv2.imread(str(path))
        if image is None:
            raise ValueError(f'Cannot read image: {path}')
        current_size = (image.shape[1], image.shape[0])
        if size is not None and current_size != size:
            raise ValueError(f'All images must have the same resolution: {path}')
        size = current_size
        corners, ids, _, _ = detector.detectBoard(image)
        if ids is None or len(ids) < 6:
            skipped.append({'image': str(path), 'reason': 'Fewer than six ChArUco corners'})
            continue
        obj, img = board.matchImagePoints(corners, ids)
        obj = obj.reshape(-1, 3)
        img = img.reshape(-1, 2)
        if np.linalg.matrix_rank(obj - obj.mean(axis=0)) < 2:
            skipped.append({'image': str(path), 'reason': 'Collinear ChArUco corners'})
            continue
        objects.append(obj.astype(np.float32))
        pixels.append(img.astype(np.float32))
        views.append({'image': str(path), 'corners': len(ids), 'corner_ids': ids.ravel().tolist()})
        if overlay_dir is not None:
            target = Path(overlay_dir) / f'{index:04d}_{Path(path).stem}.png'
            target.parent.mkdir(parents=True, exist_ok=True)
            cv2.aruco.drawDetectedCornersCharuco(image, corners, ids)
            if not cv2.imwrite(str(target), image):
                raise OSError(f'Cannot write overlay: {target}')
    if len(views) < min_views:
        reasons = '; '.join(f"{s['image']}: {s['reason']}" for s in skipped)
        raise ValueError(f'Need {min_views} usable views; found {len(views)} of {len(images)}. {reasons}')
    rms, K, D, rvecs, tvecs, std_intrinsics, _, per_view = cv2.calibrateCameraExtended(
        objects, pixels, size, None, None,
        flags=0,
        criteria=(cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_COUNT, 100, 1e-9),
    )
    if not np.all(np.isfinite(K)) or not np.all(np.isfinite(D)) or K[0, 0] <= 0 or K[1, 1] <= 0:
        raise ValueError('Calibration did not produce finite, positive focal lengths')
    errors = []
    for view, obj, img, rv, tv, view_rms in zip(views, objects, pixels, rvecs, tvecs, per_view):
        projected = cv2.projectPoints(obj, rv, tv, K, D)[0].reshape(-1, 2)
        error = np.linalg.norm(projected - img, axis=1)
        errors.extend(error.tolist())
        view.update(rms_px=float(view_rms[0]), reprojection_median_px=float(np.median(error)),
                    reprojection_p95_px=float(np.percentile(error, 95)))
    all_pixels = np.concatenate(pixels)
    return {
        'width': size[0], 'height': size[1], 'K': K.tolist(), 'D': D.ravel().tolist(),
        'distortion_model': 'plumb_bob', 'distortion_order': ['k1', 'k2', 'p1', 'p2', 'k3'],
        'board_id': spec['board_id'], 'spec_version': spec['version'],
        'method': 'ChArUco without prior intrinsics; calibrateCameraExtended, flags=0',
        'rms_px': float(rms), 'reprojection_median_px': float(np.median(errors)),
        'reprojection_p95_px': float(np.percentile(errors, 95)),
        'input_images': len(images), 'used_images': len(views), 'skipped_images': skipped,
        'views': views, 'total_corners': sum(len(p) for p in pixels),
        'corner_bounds_normalized_xy': (np.array([all_pixels.min(axis=0), all_pixels.max(axis=0)]) / size).tolist(),
        'intrinsic_std': std_intrinsics.ravel().tolist(),
        'intrinsic_std_order': ['fx', 'fy', 'cx', 'cy', 'k1', 'k2', 'p1', 'p2', 'k3',
                                'k4', 'k5', 'k6', 's1', 's2', 's3', 's4', 'tau_x', 'tau_y'],
        'limitation': 'Fit residuals and model standard deviations do not establish physical accuracy. '
                      'Use diverse views and independent validation; keep focus and resolution fixed.',
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('images', nargs='+', help='Image files, directories, or quoted globs')
    parser.add_argument('--spec', default=str(DEFAULT_SPEC), help='Matching board specification')
    parser.add_argument('--min-views', type=int, default=10, help='Minimum usable views (default: 10; minimum: 3)')
    parser.add_argument('--output', default='build/intrinsics.json', help='Camera parameters and diagnostics (.json/.yaml)')
    parser.add_argument('--overlay-dir', help='Optional directory for detected-corner previews')
    args = parser.parse_args()
    try:
        result = calibrate(image_paths(args.images), read_data(args.spec), args.min_views, args.overlay_dir)
        save_data(args.output, result)
    except (ValueError, OSError, cv2.error) as exc:
        parser.error(str(exc))
    print(f"Used {result['used_images']}/{result['input_images']} images; "
          f"RMS {result['rms_px']:.4f} px; skipped {len(result['skipped_images'])}. Saved {args.output}")
    for item in result['skipped_images']:
        print(f"Skipped {item['image']}: {item['reason']}")


if __name__ == '__main__':
    main()
