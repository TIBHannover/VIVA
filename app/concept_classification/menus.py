from django.urls import reverse
from menu import Menu, MenuItem

from base.tools.checks import group_required
from concept_classification.apps import ConceptClassificationConfig

review_children = (
    MenuItem("Positive", reverse("concept_classification:data_review_positive")),
    MenuItem("Neutral", reverse("concept_classification:data_review_neutral")),
    MenuItem("Negative", reverse("concept_classification:data_review_negative")),
)

data_children = (
    MenuItem("Select Concept", reverse("concept_classification:data_concept_selection")),
    MenuItem("Sequence Annotation", reverse("concept_classification:data_sequence_annotation")),
    MenuItem("Webcrawler", reverse("concept_classification:data_webcrawler")),
    MenuItem("Similarity Search", reverse("concept_classification:data_similarity_search")),
    MenuItem("Review", "concept_classification:data_review", children=review_children)
)
model_children = (
    MenuItem("Dataset Overview", reverse("concept_classification:model_dataset_overview")),
    MenuItem("Training", reverse("concept_classification:model_training")),
    MenuItem("Evaluation", reverse("concept_classification:model_evaluation")),
    MenuItem("Inference", reverse("concept_classification:model_inference"))
)

# reversed need to be unique otherwise wrong assumptions when resolving which menu item is selected
Menu.add_item(f"{ConceptClassificationConfig.name}_main", MenuItem("Data",
                                                                   "concept_classification:data",
                                                                   children=data_children,
                                                                   check=group_required("Annotator")))
Menu.add_item(f"{ConceptClassificationConfig.name}_main", MenuItem("Model", "concept_classification:model",
                                                                   children=model_children,
                                                                   check=group_required("Trainer")))
Menu.add_item(f"{ConceptClassificationConfig.name}_main", MenuItem("Retrieval",
                                                                   reverse("concept_classification:retrieval")))
Menu.add_item(f"{ConceptClassificationConfig.name}_main", MenuItem("Export",
                                                                   reverse("concept_classification:export")))
