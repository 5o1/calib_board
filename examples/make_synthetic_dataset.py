"""Render a repeatable PDF-based dataset for both calibration commands."""
import argparse
from pathlib import Path

import cv2
import numpy as np

from calib_board.common import DEFAULT_SPEC, read_data, save_json
from calib_board.generate import generate
from calib_board.synthetic import pose, render, workcell_pose


def make_dataset(output, spec_path=DEFAULT_SPEC):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    spec = read_data(spec_path)
    K = np.array([[906.561, 0, 647.896], [0, 905.986, 362.233], [0, 0, 1.]])
    camera = {'width': 1280, 'height': 720, 'K': K.tolist(), 'D': [0.] * 5,
              'distortion_model': 'plumb_bob'}
    pdf = generate(spec_path, output / 'board.pdf', preview=False)
    save_json(output / 'known_intrinsics.json', camera)
    directory = output / 'intrinsics'
    directory.mkdir(exist_ok=True)
    for i in range(18):
        transform = pose(spec, .60 + .04 * (i % 5), 15 + 12 * (i % 3), i * 37, (i % 5 - 2) * 5)
        transform[:2, 3] += [(i % 3 - 1) * .21, (i // 3 % 3 - 1) * .10]
        image = render(spec, transform, K, [1280, 720], pdf=pdf, noise_seed=100 + i)
        if not cv2.imwrite(str(directory / f'view_{i:02d}.png'), image):
            raise OSError('Cannot save synthetic intrinsic image')
    board_world = np.diag([1., -1., -1., 1.])
    board_world[:3, 3] = [-.15, .125, .005]
    camera_board, _ = workcell_pose(spec, .725, .9, 90)
    world_camera = board_world @ np.linalg.inv(camera_board)
    observations = []
    for label, y in [('center', 0.), ('left', -.15), ('right', .15)]:
        placement = board_world.copy()
        placement[1, 3] += y
        image = render(spec, np.linalg.inv(world_camera) @ placement, K, [1280, 720],
                       pdf=pdf, noise_seed=17)
        if not cv2.imwrite(str(output / f'{label}.png'), image):
            raise OSError('Cannot save synthetic extrinsic image')
        save_json(output / f'{label}_placement.json', {'T_world_board': placement.tolist()})
        observations.append({'image': f'{label}.png', 'placement': f'{label}_placement.json'})
    save_json(output / 'manifest.json', {'intrinsics': 'known_intrinsics.json', 'observations': observations})
    save_json(output / 'truth.json', {**camera, 'T_world_camera_optical': world_camera.tolist(),
                                    'intrinsic_noise_seeds': list(range(100, 118)), 'extrinsic_noise_seed': 17,
                                    'board_id': spec['board_id'], 'spec_version': spec['version'],
                                    'limitation': 'Synthetic pinhole images with zero distortion; not physical validation'})
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default='build/demo', help='Dataset directory')
    parser.add_argument('--spec', default=str(DEFAULT_SPEC))
    args = parser.parse_args()
    make_dataset(args.output, args.spec)
    print(f'Saved 18 intrinsic views, three measured extrinsic views, and truth to {args.output}')


if __name__ == '__main__':
    main()
