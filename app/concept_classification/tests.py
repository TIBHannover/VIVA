import json

from django.contrib.auth.models import User, Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse

from base.models import Class, Classtype, Image, Imageurl, Collection, Imageannotation, Model, Imageprediction, \
    Evaluation
from viva.settings import SessionConfig, GridConfig


class BasicVivaTest(TestCase):
    """This class provides a database initialization with very common objects"""
    @classmethod
    def setUpTestData(cls):
        cls.groups = [Group.objects.create(name='Annotator'), Group.objects.create(name='Trainer')]
        cls.user = User.objects.create_user(username='test', email='temporary@gmail.com', password='nix')
        cls.user.groups.add(*cls.groups)
        # Classtypes need to be declared here to preserve their IDs ...
        # ... because the app relies on them and pk sequences are not automatically reset.
        cls.classtype = Classtype.objects.create(id=1, name='Concept')
        cls.classtype2 = Classtype.objects.create(id=2, name='Person')


class ConceptListViewTest(BasicVivaTest):
    @classmethod
    def setUpTestData(cls):
        super(ConceptListViewTest, cls).setUpTestData()

    def setUp(self):
        self.client = Client()
        self.client.login(username='test', password='nix')

    def test_list_concepts(self):
        """List all existing concepts and no classes of other classtypes"""
        klass1 = Class.objects.create(name='Test Concept', description="Test", classtypeid=self.classtype)
        klass2 = Class.objects.create(name='Test Person', description="Test", classtypeid=self.classtype2)
        klass3 = Class.objects.create(name='Another Concept', description="Test", classtypeid=self.classtype)
        response = self.client.get(reverse("concept_classification:data_concept_selection"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context_data['object_list'].count(), 2)
        self.assertIn(klass1, response.context_data['object_list'])
        self.assertNotIn(klass2, response.context_data['object_list'])
        self.assertIn(klass3, response.context_data['object_list'])

    def test_no_concepts(self):
        """No concepts exist"""
        Class.objects.create(name='Test Person', description="Test", classtypeid=self.classtype2)
        response = self.client.get(reverse("concept_classification:data_concept_selection"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context_data['object_list'].count(), 0)


class ConceptCreateViewTest(BasicVivaTest):
    @classmethod
    def setUpTestData(cls):
        super(ConceptCreateViewTest, cls).setUpTestData()

    def setUp(self):
        self.client = Client()
        self.client.login(username='test', password='nix')

    def test_new_concept(self):
        """A valid new concept is provided"""
        response = self.client.post(reverse("concept_classification:add_concept"),
                                    {'name': "New Concept", 'description': "Foo", 'classtypeid': self.classtype.id},
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Class.objects.filter(name="New Concept").exists())
        self.assertEqual(Class.objects.get(name="New Concept").classtypeid.id, self.classtype.id)

    def test_existing_concept(self):
        """An existing concept is provided"""
        response = self.client.post(reverse("concept_classification:add_concept"),
                                    {'name': "Test Concept", 'description': "Foo", 'classtypeid': self.classtype.id},
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Class.objects.filter(name="New Concept").exists())


class SelectConceptTest(BasicVivaTest):
    @classmethod
    def setUpTestData(cls):
        super(SelectConceptTest, cls).setUpTestData()
        cls.klass = Class.objects.create(name='Test Concept', classtypeid=cls.classtype)

    def setUp(self):
        self.client = Client()
        self.client.login(username='test', password='nix')

    def test_select_concept(self):
        """A valid concept is provided"""
        response = self.client.post(reverse("concept_classification:select_concept"), {'concept': "Test Concept"},
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.session[SessionConfig.SELECTED_CONCEPT_SESSION_KEY], self.klass.id)

    def test_change_concept(self):
        """A valid concept has already been selected when another one is chosen"""
        klass = Class.objects.create(name='Selected Concept', classtypeid=self.classtype)
        s = self.client.session
        s.update({SessionConfig.SELECTED_CONCEPT_SESSION_KEY: klass.id, })
        s.save()
        response = self.client.post(reverse("concept_classification:select_concept"), {'concept': "Test Concept"},
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.session[SessionConfig.SELECTED_CONCEPT_SESSION_KEY], self.klass.id)

    def test_non_existent(self):
        """The provided concept is not resident in database"""
        response = self.client.post(reverse("concept_classification:select_concept"), {'concept': "Test Person"},
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 422)

    def test_wrong_classtype(self):
        """The provided class does not have the expected classtype ID (1 for concept)"""
        Class.objects.create(name='Test Person', classtypeid=self.classtype2)
        response = self.client.post(reverse("concept_classification:select_concept"), {'concept': "Test Person"},
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 422)


class WebCrawlerTemplateViewTest(BasicVivaTest):
    @classmethod
    def setUpTestData(cls):
        super(WebCrawlerTemplateViewTest, cls).setUpTestData()
        cls.klass = Class.objects.create(name='Test Concept', classtypeid=cls.classtype)

    def setUp(self):
        self.client = Client()
        self.client.login(username='test', password='nix')

    def test_web_crawler_template(self):
        s = self.client.session
        s.update({SessionConfig.SELECTED_CONCEPT_SESSION_KEY: self.klass.id, })
        s.save()
        response = self.client.get(reverse("concept_classification:data_webcrawler"))
        self.assertEqual(response.status_code, 200)

    def no_concept_selected(self):
        response = self.client.get(reverse("concept_classification:data_webcrawler"), follow=True)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("concept_classification:select_concept"))


class WebCrawlerQueryTest(BasicVivaTest):
    @classmethod
    def setUpTestData(cls):
        super(WebCrawlerQueryTest, cls).setUpTestData()
        cls.klass = Class.objects.create(name='Test Concept', classtypeid=cls.classtype)

    def setUp(self):
        self.client = Client()
        self.client.login(username='test', password='nix')

    def test_web_crawler_query(self):
        for type_param, license_param in [("default", "default"), ("face", "default"), ("photo", "noncommercial")]:
            with self.subTest(type_param=type_param, license_param=license_param):
                response = self.client.post(reverse("concept_classification:data_web_crawler_query"),
                                            {"text": "text", "type": type_param, "max": "50", "license": license_param},
                                            HTTP_X_REQUESTED_WITH='XMLHttpRequest', HTTP_USER_AGENT='Mozilla/5.0')
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, "download_url")
                response_content = json.loads(response.content)['elements']
                for i in range(len(response_content)):
                    self.assertEqual(response_content[i]['media_type'], "image")
                    self.assertEqual(response_content[i]['downloaded'], False)

    def test_local_image_usage(self):
        """When an image has already been downloaded before, the path and annotation of the respective db image should
        be returned"""
        collection = Collection.objects.create(basepath="webcrawler", name="Webcrawler")
        image = Image.objects.create(collectionid=collection, path="path/to/image.jpg")
        response = self.client.post(reverse("concept_classification:data_web_crawler_query"),
                                    {"text": "text", "type": "default", "max": "50", "license": "default"},
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest', HTTP_USER_AGENT='Mozilla/5.0')
        download_url = json.loads(response.content)['elements'][0]["download_url"]
        image_url = Imageurl.objects.create(imageid=image, url=download_url, downloaded=True, error=False)
        annotation = Imageannotation.objects.create(difficult=False, groundtruth=True, classid=self.klass,
                                                    imageid=image)
        response = self.client.post(reverse("concept_classification:data_web_crawler_query"),
                                    {"text": "text", "type": "default", "max": "50", "license": "default"},
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest', HTTP_USER_AGENT='Mozilla/5.0')
        self.assertEqual(response.status_code, 200)
        response_content = json.loads(response.content)['elements']
        for i in range(len(response_content)):
            self.assertEqual(response_content[i]['media_type'], "image")
            if response_content[i]['downloaded']:
                self.assertEqual(response_content[i]['id'], image.id)
                self.assertEqual(response_content[i]['url'], image.path.url)
                self.assertEqual(response_content[i]['download_error'], image_url.error)
                self.assertEqual(response_content[i]['annotation']['difficult'], annotation.difficult)
                self.assertEqual(response_content[i]['annotation']['groundtruth'], annotation.groundtruth)

    def test_insufficient_parameters(self):
        params_dicts = [{"text": "text", "type": "default", "max": "50"},
                        {"text": "text", "type": "default", "license": "default"},
                        {"text": "text", "max": "50", "license": "default"},
                        {"type": "default", "max": "50", "license": "default"}]
        for param_dict in params_dicts:
            with self.subTest(param_dict=param_dict):
                response = self.client.post(reverse("concept_classification:data_web_crawler_query"),
                                            param_dict, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
                self.assertEqual(response.status_code, 400)
        response = self.client.post(reverse("concept_classification:data_web_crawler_query"),
                                    {"text": "text", "type": "default", "max": "50", "license": "default"})
        self.assertEqual(response.status_code, 400)

    def test_invalid_parameters(self):
        """When invalid parameters are selected, expect default search"""
        params_dicts = [{"text": "text", "type": "default", "max": "50", "license": "invalid"},
                        {"text": "text", "type": "default", "max": "invalid", "license": "default"},
                        {"text": "text", "type": "invalid", "max": "50", "license": "default"}]
        for param_dict in params_dicts:
            with self.subTest(param_dict=param_dict):
                response = self.client.post(reverse("concept_classification:data_web_crawler_query"), param_dict,
                                            HTTP_X_REQUESTED_WITH='XMLHttpRequest', HTTP_USER_AGENT='Mozilla/5.0')
                self.assertEqual(response.status_code, 400)

    def test_get(self):
        response = self.client.get(reverse("concept_classification:data_web_crawler_query"),
                                   HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 400)


class SimilaritySearchTest(BasicVivaTest):
    @classmethod
    def setUpTestData(cls):
        super(SimilaritySearchTest, cls).setUpTestData()

    def setUp(self):
        self.client = Client()
        self.client.login(username='test', password='nix')

    def test_annotations(self):
        """Test review for each possible annotation"""
        klass = Class.objects.create(name='Test Concept', classtypeid=self.classtype)
        s = self.client.session
        s.update({SessionConfig.SELECTED_CONCEPT_SESSION_KEY: klass.id, })
        s.save()
        response = self.client.get(reverse("concept_classification:data_similarity_search"))
        self.assertEqual(response.status_code, 200)

    def no_concept_selected(self):
        response = self.client.get(reverse("concept_classification:data_similarity_search"))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("concept_classification:select_concept"))


class SimilaritySearchQueryTest(BasicVivaTest):
    @classmethod
    def setUpTestData(cls):
        super(SimilaritySearchQueryTest, cls).setUpTestData()
        cls.klass = Class.objects.create(name='Test Concept', classtypeid=cls.classtype)
        cls.collection = Collection.objects.create(basepath="webcrawler", name="Webcrawler")

    def setUp(self):
        self.client = Client()
        self.client.login(username='test', password='nix')
        s = self.client.session
        s.update({SessionConfig.SELECTED_CONCEPT_SESSION_KEY: self.klass.id, })
        s.save()
        self.param_dict = {GridConfig.PARAMETER_ELEMENT_COUNT: "9", GridConfig.PARAMETER_PAGE: "1"}

    def test_url(self):
        """Expect query to be accepted and processed but no EL results since DB is empty."""
        self.param_dict.update({"mode": "url", "select": "", "max": "50", "url":
            "https://www.uni-marburg.de/de/fb12/bilder/mzg_1.jpg/@@images/image/unimr_intro_image_sd"})
        response = self.client.post(reverse("concept_classification:data_similarity_search_query"),
                                    self.param_dict, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.content, b'No EL results')

    def test_upload(self):
        """Expect query to be accepted and processed but no EL results since DB is empty."""
        filepath = "base/static/images/viva-logo.png"
        with open(filepath, 'rb') as f:
            upload = SimpleUploadedFile(filepath, f.read(), content_type="image/png")
        self.param_dict.update({"mode": "upload", "select": "", "max": "50", "url": "", "file": upload})
        response = self.client.post(reverse("concept_classification:data_similarity_search_query"),
                                    self.param_dict, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.content, b'No EL results')

    def test_select(self):
        """Expect query to be accepted and processed but no EL results since DB is empty."""
        # TODO Set filepath to existing file. Remove return statement afterwards!
        return
        image_path = "dra_keyframes/images/128547/61000.jpg"
        select_image = Image.objects.create(collectionid=self.collection, path=image_path)
        self.param_dict.update({"mode": "select", "select": select_image.id, "max": "50", "url": ""})
        response = self.client.post(reverse("concept_classification:data_similarity_search_query"),
                                    self.param_dict, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.content, b'No EL results')

    def test_insufficient_parameters(self):
        param_dicts = [{"mode": "url", "select": "", "max": "50"},
                       {"mode": "url", "select": "", "url":
                        "https://www.uni-marburg.de/de/fb12/bilder/mzg_1.jpg/@@images/image/unimr_intro_image_sd"},
                       {"mode": "url", "max": "50", "url":
                        "https://www.uni-marburg.de/de/fb12/bilder/mzg_1.jpg/@@images/image/unimr_intro_image_sd"},
                       {"select": "valid", "max": "50", "url":
                        "https://www.uni-marburg.de/de/fb12/bilder/mzg_1.jpg/@@images/image/unimr_intro_image_sd"}
                       ]
        for param_dict in param_dicts:
            with self.subTest(param_dict=param_dict):
                response = self.client.post(reverse("concept_classification:data_similarity_search_query"),
                                            param_dict, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
                self.assertEqual(response.status_code, 400)

    def test_invalid_parameters(self):
        # URL is not an image or invalid
        invalid_urls = ["http://example.net", "completely/invalid"]
        for url in invalid_urls:
            with self.subTest(url=url):
                response = self.client.post(reverse("concept_classification:data_similarity_search_query"),
                                            {"mode": "url", "url": url, "select": "", "max": "50"},
                                            HTTP_X_REQUESTED_WITH='XMLHttpRequest')
                self.assertEqual(response.status_code, 400)

        # max is not a number
        response = self.client.post(reverse("concept_classification:data_similarity_search_query"),
                                    {"mode": "url", "url": "", "select": "", "max": "invalid"},
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 400)

    def test_get(self):
        response = self.client.get(reverse("concept_classification:data_similarity_search"),
                                   HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)


class ReviewTest(BasicVivaTest):
    @classmethod
    def setUpTestData(cls):
        super(ReviewTest, cls).setUpTestData()
        cls.klass = Class.objects.create(name='Test Concept', classtypeid=cls.classtype)

    def setUp(self):
        self.client = Client()
        self.client.login(username='test', password='nix')

    def test_review(self):
        """Test review for each possible annotation"""
        s = self.client.session
        s.update({SessionConfig.SELECTED_CONCEPT_SESSION_KEY: self.klass.id, })
        s.save()
        for annotation in ["positive", "neutral", "negative"]:
            with self.subTest(annotation=annotation):
                response = self.client.post(reverse(f"concept_classification:data_review_{annotation}"))
                self.assertEqual(response.status_code, 200)

    def no_concept_selected(self):
        for annotation in ["positive", "neutral", "negative"]:
            with self.subTest(annotation=annotation):
                response = self.client.post(reverse(f"concept_classification:data_review_{annotation}"))
                self.assertEqual(response.status_code, 302)
                self.assertRedirects(response, reverse("concept_classification:select_concept"))


class ReviewQueryTest(BasicVivaTest):
    @classmethod
    def setUpTestData(cls):
        super(ReviewQueryTest, cls).setUpTestData()
        cls.klass = Class.objects.create(name='Test Concept', classtypeid=cls.classtype)

    def setUp(self):
        self.client = Client()
        self.client.login(username='test', password='nix')
        s = self.client.session
        s.update({SessionConfig.SELECTED_CONCEPT_SESSION_KEY: self.klass.id, })
        s.save()

    def test_annotations(self):
        """Create all kinds of annotations and query review with each of those"""
        collection = Collection.objects.create(basepath="webcrawler", name="Webcrawler")
        image = Image.objects.create(collectionid=collection, path="path/to/image.jpg")
        Imageannotation.objects.create(difficult=True, groundtruth=True, classid=self.klass,
                                       imageid=image, userid=self.user)
        image2 = Image.objects.create(collectionid=collection, path="path/to/image2.jpg")
        Imageannotation.objects.create(difficult=False, groundtruth=True, classid=self.klass,
                                       imageid=image2, userid=self.user)
        image3 = Image.objects.create(collectionid=collection, path="path/to/image3.jpg")
        Imageannotation.objects.create(difficult=True, groundtruth=False, classid=self.klass,
                                       imageid=image3, userid=self.user)
        image4 = Image.objects.create(collectionid=collection, path="path/to/image4.jpg")
        Imageannotation.objects.create(difficult=False, groundtruth=False, classid=self.klass,
                                       imageid=image4, userid=self.user)
        img_dicts = [
            {"id": image.id, "url": image.path.url, "media_type": "image"},
            {"id": image3.id, "url": image3.path.url, "media_type": "image"},
            {"id": image4.id, "url": image4.path.url, "media_type": "image"},
            {"id": image2.id, "url": image2.path.url, "media_type": "image"}
        ]
        param_dicts = [{"difficult": "1", "groundtruth": "1"}, {"difficult": "1", "groundtruth": "0"},
                       {"difficult": "0", "groundtruth": "0"}, {"difficult": "0", "groundtruth": "1"}]
        for i, param_dict in enumerate(param_dicts):
            with self.subTest(param_dict=param_dict):
                param_dict.update({GridConfig.PARAMETER_ELEMENT_COUNT: "9", GridConfig.PARAMETER_PAGE: "1"})
                response = self.client.post(reverse("concept_classification:data_review_query"),
                                            param_dict, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
                self.assertEqual(response.status_code, 200)
                self.assertJSONEqual(response.content, {'elements': [img_dicts[i]], 'count': 1})

    def test_insufficient_parameters(self):
        param_dicts = [{"difficult": True}, {"groundtruth": False}]
        for param_dict in param_dicts:
            with self.subTest(param_dict=param_dict):
                response = self.client.post(reverse("concept_classification:data_review_query"),
                                            param_dict, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
                self.assertEqual(response.status_code, 400)

    def test_get(self):
        response = self.client.get(reverse("concept_classification:data_review_query"),
                                   HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 400)


class DatasetOverviewTest(BasicVivaTest):
    @classmethod
    def setUpTestData(cls):
        super(DatasetOverviewTest, cls).setUpTestData()

    def setUp(self):
        self.client = Client()
        self.client.login(username='test', password='nix')

    def test_dataset_overview_with_concept(self):
        Class.objects.create(name='Test Concept', classtypeid=self.classtype)
        response = self.client.get(reverse("concept_classification:model_dataset_overview"))
        self.assertEqual(response.status_code, 200)
        # templates and context not available in with jinja2, see https://code.djangoproject.com/ticket/24622
        # self.assertTemplateUsed(response, "concept_classification/model-dataset.html")

    def test_dataset_overview_without_concept(self):
        response = self.client.get(reverse("concept_classification:model_dataset_overview"))
        self.assertEqual(response.status_code, 200)
        # templates and context not available in with jinja2, see https://code.djangoproject.com/ticket/24622
        # self.assertTemplateUsed(response, "concept_classification/model-dataset.html")


class TrainServerTemplateTest(BasicVivaTest):
    @classmethod
    def setUpTestData(cls):
        super(TrainServerTemplateTest, cls).setUpTestData()

    def setUp(self):
        self.client = Client()
        self.client.login(username='test', password='nix')

    def test_train_server_template(self):
        """Test template for training and inference"""
        for mode in ["training", "inference"]:
            with self.subTest(mode=mode):
                response = self.client.get(reverse(f"concept_classification:model_{mode}"))
                self.assertEqual(response.status_code, 200)


class EvaluationTest(BasicVivaTest):
    @classmethod
    def setUpTestData(cls):
        super(EvaluationTest, cls).setUpTestData()

    def setUp(self):
        self.client = Client()
        self.client.login(username='test', password='nix')

    def test_dataset_overview_with_concept(self):
        Class.objects.create(name='Test Concept', classtypeid=self.classtype)
        response = self.client.get(reverse(f"concept_classification:model_evaluation"))
        self.assertEqual(response.status_code, 200)
        # templates and context not available in with jinja2, see https://code.djangoproject.com/ticket/24622
        # self.assertTemplateUsed(response, "concept_classification/model-evaluation.html")

    def test_dataset_overview_without_concept(self):
        response = self.client.get(reverse(f"concept_classification:model_evaluation"))
        self.assertEqual(response.status_code, 200)
        # templates and context not available in with jinja2, see https://code.djangoproject.com/ticket/24622
        # self.assertTemplateUsed(response, "concept_classification/model-evaluation.html")


class RetrievalViewTest(BasicVivaTest):
    @classmethod
    def setUpTestData(cls):
        super(RetrievalViewTest, cls).setUpTestData()

    def setUp(self):
        self.client = Client()
        self.client.login(username='test', password='nix')

    def test_retrieval(self):
        response = self.client.get(reverse("concept_classification:retrieval"))
        self.assertEqual(response.status_code, 200)


class RetrievalQueryTest(BasicVivaTest):
    @classmethod
    def setUpTestData(cls):
        super(RetrievalQueryTest, cls).setUpTestData()
        cls.klass = Class.objects.create(name='Test Concept', classtypeid=cls.classtype)
        cls.klass2 = Class.objects.create(name='Another Concept', classtypeid=cls.classtype)

    def setUp(self):
        self.client = Client()
        self.client.login(username='test', password='nix')

        model = Model.objects.create(date="2020-06-07 00:13:02.000000", inference_stored=True,
                                     dir_name="2020-06-07_00-13-02")
        collection = Collection.objects.create(basepath="webcrawler", name="Webcrawler")
        image = Image.objects.create(collectionid=collection, path="path/to/image.jpg")
        Evaluation.objects.create(modelid=model, classid=self.klass, precision=0.9)
        Evaluation.objects.create(modelid=model, classid=self.klass2, precision=0.8)

        Imageannotation.objects.create(difficult=False, groundtruth=True, classid=self.klass,
                                       imageid=image, userid=self.user)
        self.ip = Imageprediction.objects.create(score=0.8, classid=self.klass, imageid=image, modelid=model)

        image2 = Image.objects.create(collectionid=collection, path="path/to/image2.jpg")
        Imageannotation.objects.create(difficult=True, groundtruth=True, classid=self.klass,
                                       imageid=image2, userid=self.user)
        self.ip2 = Imageprediction.objects.create(score=0.78, classid=self.klass, imageid=image2, modelid=model)

        image3 = Image.objects.create(collectionid=collection, path="path/to/image3.jpg")
        self.ip3 = Imageprediction.objects.create(score=0.66, classid=self.klass, imageid=image3, modelid=model)
        # annotate with another concept, this needs to be filtered out when using annotations = False option
        Imageannotation.objects.create(difficult=False, groundtruth=False, classid=self.klass2,
                                       imageid=image2, userid=self.user)

        image4 = Image.objects.create(collectionid=collection, path="path/to/image4.jpg")
        self.ip4 = Imageprediction.objects.create(score=0.9, classid=self.klass, imageid=image4, modelid=model)

        self.ip_dict, self.ip2_dict, self.ip3_dict, self.ip4_dict = [
            {'id': self.ip.imageid_id, 'url': self.ip.imageid.path.url,
             'media_type': 'image', 'score': self.ip.score},
            {'id': self.ip2.imageid_id, 'url': self.ip2.imageid.path.url,
             'media_type': 'image', 'score': self.ip2.score},
            {'id': self.ip3.imageid_id, 'url': self.ip3.imageid.path.url,
             'media_type': 'image', 'score': self.ip3.score},
            {'id': self.ip4.imageid_id, 'url': self.ip4.imageid.path.url,
             'media_type': 'image', 'score': self.ip4.score}
        ]

    def test_annotations_ascending(self):
        response = self.client.post(reverse("concept_classification:retrieval_query"),
                                    {"concept": self.klass.id, "asc": "1", "annotations": "1",
                                     GridConfig.PARAMETER_ELEMENT_COUNT: "9", GridConfig.PARAMETER_PAGE: "1"},
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        json_response = json.loads(response.content)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(json_response["elements"]), 4)
        self.assertEqual(json_response["count"], 4)
        self.assertEqual(json_response["elements"], [self.ip3_dict, self.ip2_dict, self.ip_dict, self.ip4_dict])

    def test_annotations_decending(self):
        response = self.client.post(reverse("concept_classification:retrieval_query"),
                                    {"concept": self.klass.id, "asc": "0", "annotations": "1",
                                     GridConfig.PARAMETER_ELEMENT_COUNT: "9", GridConfig.PARAMETER_PAGE: "1"},
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        json_response = json.loads(response.content)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(json_response["elements"]), 4)
        self.assertEqual(json_response["count"], 4)
        self.assertEqual(json_response["elements"], [self.ip4_dict, self.ip_dict, self.ip2_dict, self.ip3_dict])

    def test_no_annotations_ascending(self):
        response = self.client.post(reverse("concept_classification:retrieval_query"),
                                    {"concept": self.klass.id, "asc": "1", "annotations": "0",
                                     GridConfig.PARAMETER_ELEMENT_COUNT: "9", GridConfig.PARAMETER_PAGE: "1"},
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        json_response = json.loads(response.content)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(json_response["elements"]), 2)
        self.assertEqual(json_response["count"], 2)
        self.assertEqual(json_response["elements"], [self.ip3_dict, self.ip4_dict])

    def test_no_annotations_decending(self):
        response = self.client.post(reverse("concept_classification:retrieval_query"),
                                    {"concept": self.klass.id, "asc": "0", "annotations": "0",
                                     GridConfig.PARAMETER_ELEMENT_COUNT: "9", GridConfig.PARAMETER_PAGE: "1"},
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        json_response = json.loads(response.content)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(json_response["elements"]), 2)
        self.assertEqual(json_response["count"], 2)
        self.assertEqual(json_response["elements"], [self.ip4_dict, self.ip3_dict])

    def test_insufficient_parameters(self):
        params_dicts = [{"concept": self.klass, "asc": True}, {"concept": self.klass, "annotations": True},
                        {"asc": True, "annotations": True}]
        for param_dict in params_dicts:
            with self.subTest(param_dict=param_dict):
                response = self.client.post(reverse("concept_classification:retrieval_query"),
                                            param_dict, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
                self.assertEqual(response.status_code, 400)

    def test_invalid_parameters(self):
        response = self.client.post(reverse("concept_classification:retrieval_query"),
                                    {"concept": "Invalid", "asc": True, "annotations": True},
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 400)

    def test_get(self):
        response = self.client.get(reverse("concept_classification:retrieval_query"),
                                   HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 400)
