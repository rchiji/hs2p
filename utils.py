import os
import time
import tqdm
import numpy as np
import pandas as pd
from pathlib import Path
from typing import List, Optional, Tuple, Dict

from wsi.WholeSlideImage import WholeSlideImage
from wsi.wsi_utils import StitchCoords
from wsi.batch_process_utils import initialize_df


def segment(
	WSI_object: WholeSlideImage,
	seg_params: Optional[Dict] = None,
	filter_params: Optional[Dict] = None,
	mask_file=None
	):
	start_time = time.time()
	if mask_file is not None:
		WSI_object.initSegmentation(mask_file)
	else:
		WSI_object.segmentTissue(**seg_params, filter_params=filter_params)
	seg_time_elapsed = time.time() - start_time
	return WSI_object, seg_time_elapsed


def patching_old(WSI_object, **kwargs):
	start_time = time.time()
	file_path = WSI_object.createPatches_bag_hdf5(**kwargs, save_coord=True)
	patch_time_elapsed = time.time() - start_time
	return file_path, patch_time_elapsed


def patching(
	WSI_object: WholeSlideImage,
	save_dir: Path,
	seg_level: int,
	patch_level: int,
	patch_size: int,
	step_size: int,
	contour_fn: str,
	drop_holes: bool,
	tissue_thresh: float,
	use_padding: bool,
	save_png_to_disk: bool,
	top_left: Optional[List[int]] = None,
	bot_right: Optional[List[int]] = None,
	position: int = -1,
	verbose: bool = False,
	):
    start_time = time.time()
    file_path = WSI_object.process_contours(
		save_dir=save_dir,
		seg_level=seg_level,
		patch_level=patch_level,
		patch_size=patch_size,
		step_size=step_size,
		contour_fn=contour_fn,
		drop_holes=drop_holes,
		tissue_thresh=tissue_thresh,
		use_padding=use_padding,
		save_png_to_disk=save_png_to_disk,
		top_left=top_left,
		bot_right=bot_right,
		position=position,
		verbose=verbose,
	)
    patch_time_elapsed = time.time() - start_time
    return file_path, patch_time_elapsed


def stitching(
	file_path: Path,
	wsi_object: WholeSlideImage,
	downscale: int = 64,
	bg_color: Tuple[int,int,int] = (255,255,255),
	draw_grid: bool = False,
	position: int = -1,
	verbose: bool = False,
	):
	start = time.time()
	heatmap = StitchCoords(
		file_path,
		wsi_object,
		downscale=downscale,
		bg_color=bg_color,
		alpha=-1,
		draw_grid=draw_grid,
		position=position,
		verbose=verbose,
	)
	total_time = time.time() - start
	return heatmap, total_time


def seg_and_patch(
	data_dir: Path,
	output_dir: Path,
	patch_save_dir: Path,
	mask_save_dir: Path,
	stitch_save_dir: Path,
	seg_params,
	filter_params,
	vis_params,
	patch_params,
	slide_list: Optional[List[str]] = None,
	patch_size: int = 256,
	step_size: int = 256,
	patch_level: int = 0,
	seg: bool = False,
	stitch: bool = False,
	patch: bool = False,
	auto_skip: bool = True,
	process_list: str = None,
	verbose: bool = False,
	supported_fmts: List[str] = ['.tiff', '.tif', '.svs']
	):

	if slide_list is not None:
		with open(slide_list, 'r') as f:
			slides = sorted([s.strip() for s in f])
	else:
		slides = sorted([d for d in data_dir.iterdir()])
		slides = [slide.name for slide in slides if slide.is_file() and slide.suffix in supported_fmts]

	if process_list is None:
		df = initialize_df(slides, seg_params, filter_params, vis_params, patch_params)
	else:
		df = pd.read_csv(process_list)
		df = initialize_df(df, seg_params, filter_params, vis_params, patch_params)

	mask = df['process'] == 1
	process_stack = df[mask]

	total = len(process_stack)

	seg_times = 0.
	patch_times = 0.
	stitch_times = 0.

	with tqdm.tqdm(
        range(total),
        desc=(f'Seg&Patch'),
        unit=' slide',
        ncols=100,
		position=0,
		leave=True,
    ) as t:

		for i in t:

			df.to_csv(Path(output_dir, 'process_list_autogen.csv'), index=False)
			idx = process_stack.index[i]
			slide = process_stack.loc[idx, 'slide_id']
			t.display(f'Processing {slide}', pos=7*i+2)

			df.loc[idx, 'process'] = 0
			slide_id = Path(slide).stem

			if auto_skip and Path(patch_save_dir, slide_id + '.h5').is_file():
				print(f'{slide_id} already exist in destination location, skipped')
				df.loc[idx, 'status'] = 'already_exist'
				continue

			# Inialize WSI
			full_path = Path(data_dir, slide)
			WSI_object = WholeSlideImage(full_path)

			current_vis_params = {}
			current_filter_params = {}
			current_seg_params = {}

			for key in vis_params.keys():
				current_vis_params.update({key: df.loc[idx, key]})

			for key in filter_params.keys():
				current_filter_params.update({key: df.loc[idx, key]})

			for key in seg_params.keys():
				if key in df.columns:
					current_seg_params.update({key: df.loc[idx, key]})

			if current_vis_params['vis_level'] < 0:
				if len(WSI_object.level_dim) == 1:
					current_vis_params['vis_level'] = 0

				else:
					wsi = WSI_object.getOpenSlide()
					best_level = wsi.get_best_level_for_downsample(64)
					current_vis_params['vis_level'] = best_level

			if current_seg_params['seg_level'] < 0:
				if len(WSI_object.level_dim) == 1:
					current_seg_params['seg_level'] = 0

				else:
					wsi = WSI_object.getOpenSlide()
					best_level = wsi.get_best_level_for_downsample(64)
					current_seg_params['seg_level'] = best_level

			keep_ids = current_seg_params['keep_ids']
			if keep_ids is not None and len(keep_ids) > 0:
				str_ids = current_seg_params['keep_ids']
				current_seg_params['keep_ids'] = np.array(str_ids.split(',')).astype(int)
			else:
				current_seg_params['keep_ids'] = []

			exclude_ids = current_seg_params['exclude_ids']
			if exclude_ids is not None and len(exclude_ids) > 0:
				str_ids = current_seg_params['exclude_ids']
				current_seg_params['exclude_ids'] = np.array(str_ids.split(',')).astype(int)
			else:
				current_seg_params['exclude_ids'] = []

			w, h = WSI_object.level_dim[current_seg_params['seg_level']]
			if w * h > 1e8:
				print(f'level_dim {w} x {h} is likely too large for successful segmentation, aborting')
				df.loc[idx, 'status'] = 'failed_seg'
				continue

			df.loc[idx, 'vis_level'] = current_vis_params['vis_level']
			df.loc[idx, 'seg_level'] = current_seg_params['seg_level']


			seg_time_elapsed = -1
			if seg:
				WSI_object, seg_time_elapsed = segment(
					WSI_object,
					current_seg_params,
					current_filter_params,
				)

			if seg_params.save_mask:
				mask = WSI_object.visWSI(**current_vis_params)
				mask_path = Path(mask_save_dir, slide_id+'.jpg')
				mask.save(mask_path)

			patch_time_elapsed = -1 # Default time
			if patch:
				slide_save_dir = Path(patch_save_dir, slide_id, str(patch_size))
				slide_save_dir.mkdir(parents=True, exist_ok=True)
				file_path, patch_time_elapsed = patching(
					WSI_object=WSI_object,
					save_dir=slide_save_dir,
					seg_level=current_seg_params['seg_level'],
					patch_level=patch_level,
					patch_size=patch_size,
					step_size=step_size,
					contour_fn=patch_params.contour_fn,
					drop_holes=patch_params.drop_holes,
					tissue_thresh=patch_params.tissue_thresh,
					use_padding=patch_params.use_padding,
					save_png_to_disk=patch_params.save_png_to_disk,
					position=7*i+3,
					verbose=verbose,
				)
				# file_path, patch_time_elapsed = patching_old(WSI_object=WSI_object,  **current_patch_params)

			stitch_time_elapsed = -1
			if stitch:
				file_path = Path(patch_save_dir, slide_id, str(patch_size), f'{slide_id}.h5')
				if file_path.is_file():
					heatmap, stitch_time_elapsed = stitching(
						file_path,
						WSI_object,
						downscale=64,
						bg_color=tuple(patch_params.bg_color),
						draw_grid=patch_params.draw_grid,
						position=7*i+4,
						verbose=verbose,
					)
					stitch_path = Path(stitch_save_dir, f'{slide_id}_{patch_size}.jpg')
					heatmap.save(stitch_path)

			t.display(f'segmentation took {seg_time_elapsed:.2f}s', pos=7*i+5)
			t.display(f'patching took {patch_time_elapsed:.2f}s', pos=7*i+6)
			t.display(f'stitching took {stitch_time_elapsed:.2f}s', pos=7*i+7)
			df.loc[idx, 'status'] = 'processed'

			seg_times += seg_time_elapsed
			patch_times += patch_time_elapsed
			stitch_times += stitch_time_elapsed

	seg_times /= total
	patch_times /= total
	stitch_times /= total

	df.to_csv(Path(output_dir, 'process_list_autogen.csv'), index=False)
	print(f'\n'*(7*total))
	print('-'*7, 'summary', '-'*7,)
	print(f'average segmentation time per slide: \t{seg_times:.2f}s')
	print(f'average patching time per slide: \t{patch_times:.2f}s')
	print(f'average stiching time per slide: \t{stitch_times:.2f}s')
	print('-'*7, ' '*len('summary'), '-'*7,)

	return seg_times, patch_times
