import numpy as np
import csv
import os
import cv2
import faiss

from errors import *
from config import PATH_INDEX_FILE, PATH_LABELS_FILE, PATH_MODEL_FILE, PATH_SHAPE_PREDICTOR, MODE
from align import init_aligner, align_faces, align_faces_sim_search
from detection import init_detector, detect_faces
from encoder import embed_face



def convert_bbox_string(bboxString):
	x, y, w, h = bboxString.split(" ")
	bbox = [(int(x), int(y), int(w), int(h))]
	return bbox


def load_labels(path_lbs):
	with open(path_lbs,  'r') as f:
		reader = csv.reader(f)
		lbs = [l[:] for l in reader]
	return lbs


def load_index(path_index, mode="cpu"):
	index = faiss.read_index(path_index)
	if mode == "gpu":
		ngpus = faiss.get_num_gpus()
		if ngpus > 0:
			index = faiss.index_cpu_to_all_gpus(index)
	return index


def similarity_search(index, lbs_index, fts_q, num_nearest_neighbors=100):
	fts_array = np.asarray(fts_q, dtype=np.float32)
	D,I = index.search(fts_array, num_nearest_neighbors)
	result_lst = []
	for cnt1, I_row in enumerate(I):
		for cnt2, idx in enumerate(I_row):
			img, x, y, w, h = lbs_index[idx]
			score = D[cnt1][cnt2]
			result_lst.append({
		        "path": img,
		        "bbox": { "x": x, "y": y, "w": w, "h": h},
		        "score": score
		    })
	return result_lst


def get_similar_faces(img, max_results, query_dets):
	result_lst = []
	score_lst = []

	if query_dets==" ":
		# 1 - Detect face in query image (dlib or Retina face)
		try:
			detector = init_detector()
			dets = detect_faces(img, detector)
		except:
			raise DetectorNotFoundError()
	else:
		dets = convert_bbox_string(query_dets)
	
	if len(dets) == 0:
		raise NoFaceInImageError()

	# 2 - Align face
	try:
		fa = init_aligner()
		faces = align_faces_sim_search(img, dets, fa)
		face = faces[0]
	except:
		raise AlignerNotFoundError()

	
	# 3 - Extract feature vector for query face
	try:
		face_embedding = embed_face(face)
	except:
		raise ModelNotFoundError()

	# 4 - similarity search on faiss index
	try:
		index = load_index(PATH_INDEX_FILE, MODE)
		lbs_index = load_labels(PATH_LABELS_FILE)
	except:
		raise IndexNotFoundError()
	

	result_lst = similarity_search(index, lbs_index, [face_embedding], max_results)
	
	return result_lst


