from django.urls import reverse
from menu import Menu, MenuItem

from base.tools.checks import group_required
from face_recognition.apps import FaceRecognitionConfig

data_children = (
    MenuItem("Select Person", reverse("face_recognition:data_person_selection")),
    MenuItem("Sequence Annotation", reverse("face_recognition:data_sequence_annotation")),
    MenuItem("Webcrawler", reverse("face_recognition:data_webcrawler")),
    MenuItem("Similarity Search", reverse("face_recognition:data_similarity_search")),
    MenuItem("Review", reverse("face_recognition:data_review"))
)
model_children = (
    MenuItem("Dataset Overview", reverse("face_recognition:model_dataset_overview")),
    MenuItem("Training", reverse("face_recognition:model_training")),
    MenuItem("Evaluation", reverse("face_recognition:model_evaluation")),
    MenuItem("Inference", reverse("face_recognition:model_inference"))
)

# reversed need to unique otherwise wrong assumptions when resolving which menu item is selected
Menu.add_item(f"{FaceRecognitionConfig.name}_main", MenuItem("Data", "fr:data",
                                                             children=data_children,
                                                             check=group_required("Annotator")))
Menu.add_item(f"{FaceRecognitionConfig.name}_main", MenuItem("Model", "fr:model",
                                                             children=model_children,
                                                             check=group_required("Annotator")))
Menu.add_item(f"{FaceRecognitionConfig.name}_main", MenuItem("Retrieval",
                                                             reverse("face_recognition:retrieval")))
Menu.add_item(f"{FaceRecognitionConfig.name}_main", MenuItem("Export",
                                                             reverse("face_recognition:export")))
