import os
import csv
import json
import pickle

import h5py
import numpy as np
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse
from datetime import datetime
from sklearn.svm import SVC
from sklearn.metrics import classification_report
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import StratifiedKFold

from imblearn.under_sampling import RandomUnderSampler
from imblearn.pipeline import make_pipeline

from base.models import Model, Image, Class, Evaluation
from face_recognition.apps import FaceRecognitionConfig
from face_recognition.classifier.imageprediction import set_image_prediction, set_model_inference_stored, \
    delete_previous_model_predictions
from viva.settings import PersonTrainInferConfig


def read_labels(label_path):
    with open(label_path, "r") as f:
        reader = csv.reader(f)
        labels = [x[0] for x in reader]
        return labels


def load_encodings(encoding_path):
    features_file = h5py.File(encoding_path, 'r')
    dataset = features_file['encodings']
    encoding_list = [dataset[i].astype('float32') for i in range(len(dataset))]
    print('Loading %4d face embeddings ...' % len(dataset))
    return np.array(encoding_list)


def get_cross_val_report(report_lst, n_splits):
    cross_val_report = {}
    for i, report_dct in enumerate(report_lst):
        for classlabel, result_dct in report_dct.items():
            if classlabel not in cross_val_report:
                cross_val_report[classlabel] = result_dct
            else:
                if classlabel == "accuracy":
                    cross_val_report[classlabel] += result_dct
                    if i == n_splits - 1:
                        cross_val_report[classlabel] /= n_splits

                else:
                    for measure, score in result_dct.items():
                        cross_val_report[classlabel][measure] += score
                        if i == n_splits - 1:
                            cross_val_report[classlabel][measure] /= n_splits

    return cross_val_report


def save_and_write_model_to_db(model, classes, pre_path=PersonTrainInferConfig.PREPATH_CLASSIFIER):
    # Saving classifier model
    dt = datetime.now()
    timestamp = dt.strftime("%Y-%m-%d_%H-%M-%S")
    out_path = os.path.join(pre_path, str(timestamp) + ".pkl")

    with open(out_path, 'wb') as outfile:
        pickle.dump((model, classes), outfile)

    # create new model object
    model_obj = Model.objects.create(date=dt, dir_name=timestamp)
    return model_obj


def write_evaluation_to_db(report_dict, model_obj, classes):
    for i, classid in enumerate(classes):
        Evaluation.objects.create(modelid=model_obj, classid_id=int(classid),
                                  precision=report_dict[classid]["precision"])


def train_classifier():
    # stratified k-fold cross-validation with an imbalanced dataset

    # params
    TRAIN_RATIO = 0.8
    NUM_SAMPLING = 100
    N_SPLITS = 5

    dataset_fts_pth = PersonTrainInferConfig.PATH_TRAINING_EMBEDDING_FILE
    dataset_lbs_pth = PersonTrainInferConfig.PATH_TRAINING_EMBEDDING_LABEL_FILE

    dataset_lbs = read_labels(dataset_lbs_pth)

    # encode labels
    le = LabelEncoder()
    y = le.fit_transform(dataset_lbs)

    # load feature vector array
    X = load_encodings(dataset_fts_pth)

    # generate sampling dicts
    sampling_train = {}
    for i, label in enumerate(np.unique(y)):
        samples = int(np.count_nonzero(y == label) * TRAIN_RATIO)
        sampling_train[label] = min(NUM_SAMPLING, samples)

    # resampling strategy
    rus = RandomUnderSampler(random_state=42, sampling_strategy=sampling_train)

    # classifier
    clf = SVC(C=1000, gamma=0.001, kernel='rbf', probability=True)

    pipeline = make_pipeline(rus, clf)

    skf = StratifiedKFold(n_splits=N_SPLITS, shuffle=True, random_state=1)

    # enumerate the splits
    report_lst = []
    for train_idx, test_idx in skf.split(X, y):
        X_train, X_test = X[train_idx], X[test_idx]
        y_train, y_test = y[train_idx], y[test_idx]
        y_pred = pipeline.fit(X_train, y_train).predict(X_test)
        report = classification_report(y_test, y_pred, target_names=list(le.classes_), output_dict=True)
        report_lst.append(report)

    # save the trained model and add to db
    model_obj = save_and_write_model_to_db(clf, list(le.classes_))

    # calculate cross validation scores
    cross_val_report = get_cross_val_report(report_lst, N_SPLITS)

    # write evaluation scores to db
    write_evaluation_to_db(cross_val_report, model_obj, list(le.classes_))


def classify(request):
    evaluation_person = Evaluation.objects.filter(
        classid__classtypeid_id=FaceRecognitionConfig.class_type_id).values_list('id', flat=True)
    model = Model.objects.filter(evaluation__in=evaluation_person).latest('date')
    with open(os.path.join(PersonTrainInferConfig.PREPATH_CLASSIFIER, model.dir_name + ".pkl"), 'rb') as f:
        (clf, class_names) = pickle.load(f)

        features_file = h5py.File(PersonTrainInferConfig.PATH_EMBEDDING_FILE, 'r')
        dataset = features_file['encodings']

        with open(PersonTrainInferConfig.PATH_EMBEDDING_LABEL_FILE, "r") as fl:
            reader = csv.reader(fl)
            labels = [(x[0], int(x[1]), int(x[2]), int(x[3]), int(x[4])) for x in reader]

        for i in range(len(labels)):
            emb_array = np.array([dataset[i].astype('float32')])
            img_id, x, y, w, h = labels[i]
            predictions = clf.predict_proba(emb_array)

            best_class_indices = np.argmax(predictions, axis=1)
            best_class_probabilities = predictions[np.arange(len(best_class_indices)), best_class_indices]
            if len(best_class_indices) == 1 and len(best_class_probabilities) == 1:
                classid = int(class_names[best_class_indices[0]])
                try:
                    image_class = Class.objects.get(id=classid)
                    image = Image.objects.get(id=img_id)
                    set_image_prediction(image, image_class, model, best_class_probabilities[0])
                except ObjectDoesNotExist:
                    pass

    set_model_inference_stored(model.id)
    delete_previous_model_predictions(n=PersonTrainInferConfig.LAST_N_MODELS_TO_KEEP)

    return HttpResponse(json.dumps({'total_classifications': len(labels)}))
