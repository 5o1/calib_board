"""Solve a fixed camera's world pose directly from measured board photographs."""
import argparse
from pathlib import Path
import sys

import cv2

from .common import DEFAULT_SPEC, intrinsics, read_data, save_data, save_json
from .detect import detect
from .extrinsics import check_placements, joint_extrinsics, placement_transform


def calibrate(manifest_path, spec, intrinsics_path=None, quick_check=False, diagnostics_dir=None):
    manifest_path = Path(manifest_path)
    manifest = read_data(manifest_path)
    root = manifest_path.resolve().parent
    camera_file = intrinsics_path or manifest.get('intrinsics')
    if camera_file is None:
        raise ValueError('Provide intrinsics in the manifest or with --intrinsics')
    camera_file = Path(camera_file) if intrinsics_path else root / camera_file
    K, D, info = intrinsics(camera_file)
    observations = manifest.get('observations', [])
    if not observations:
        raise ValueError('The manifest needs a non-empty observations list')
    images = [(root / item['image']).resolve() for item in observations]
    if len(set(images)) != len(images):
        raise ValueError('Each observation must reference a different image file')
    placements = [read_data(root / item['placement']) for item in observations]
    status = check_placements(placements, spec, quick_check)
    detections, records = [], []
    for index, (image_path, item, placement) in enumerate(zip(images, observations, placements)):
        image = cv2.imread(str(image_path))
        if image is None:
            raise ValueError(f'Cannot read image: {image_path}')
        size = [image.shape[1], image.shape[0]]
        if 'width' in info and size != [info['width'], info['height']]:
            raise ValueError(f'Image resolution does not match intrinsics: {image_path}')
        detection, overlay = detect(image, spec, K, D)
        detection['image'] = str(image_path)
        detections.append(detection)
        records.append({'image': str(image_path), 'placement': str(root / item['placement']),
                        'T_world_board': placement_transform(placement, spec).tolist(),
                        'corners': len(detection['corner_ids']),
                        'reprojection_median_px': detection['reprojection_median_px']})
        if diagnostics_dir is not None:
            base = Path(diagnostics_dir) / f'{index:04d}_{image_path.stem}'
            save_json(str(base) + '_detection.json', detection)
            if not cv2.imwrite(str(base) + '_overlay.png', overlay):
                raise OSError(f'Cannot write overlay: {base}')
    result = joint_extrinsics(detections, placements, spec)
    result.update(status)
    result.update(board_id=spec['board_id'], spec_version=spec['version'],
                  K=K.tolist(), D=D.tolist(), image_size_wh=detections[0]['image_size_wh'],
                  observations=records)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest', help='JSON/YAML pairing each image with its measured board placement')
    parser.add_argument('--intrinsics', help='Override the manifest camera file (relative to the working directory)')
    parser.add_argument('--spec', default=str(DEFAULT_SPEC), help='Matching board specification')
    parser.add_argument('--output', default='build/extrinsics.json', help='World camera pose and diagnostics (.json/.yaml)')
    parser.add_argument('--diagnostics-dir', help='Optional directory for detections and overlays')
    parser.add_argument('--quick-check', action='store_true', help='Allow fewer than three placements; diagnostic output only')
    args = parser.parse_args()
    try:
        result = calibrate(args.manifest, read_data(args.spec), args.intrinsics, args.quick_check, args.diagnostics_dir)
        save_data(args.output, result)
    except (ValueError, OSError, KeyError, cv2.error) as exc:
        parser.error(str(exc))
    if args.quick_check:
        print('Warning: quick-check output is diagnostic only; calibration requires at least three distinct board placements.', file=sys.stderr)
    print(f"Used {result['images']} images, {result['distinct_placements']} placements; "
          f"median {result['reprojection_median_px']:.4f} px. Saved {args.output}")


if __name__ == '__main__':
    main()
