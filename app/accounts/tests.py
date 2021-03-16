from django.contrib import auth
from django.contrib.auth.hashers import check_password
from django.contrib.auth.models import User, Group
from django.test import Client, TestCase
from django.urls import reverse

from base.models import Collection, Image, Imageannotation, Classtype, Class


class BasicAccountsTest(TestCase):
    """This class provides a database initialization with very common objects"""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username="test", email="temporary@gmail.com", password='nix',
                                            first_name="Firstname", last_name="Surname")


class UserUpdateViewTest(BasicAccountsTest):
    @classmethod
    def setUpTestData(cls):
        super(UserUpdateViewTest, cls).setUpTestData()

    def setUp(self):
        self.client = Client()
        self.client.login(username='test', password='nix')

    def test_update_first_name(self):
        response = self.client.post(reverse("accounts:profile"), {'first_name': "John",
                                                                  'username': self.user.username,
                                                                  'email': self.user.email,
                                                                  'last_name': self.user.last_name})
        user = User.objects.get(id=self.user.id)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("accounts:profile"))
        self.assertEqual(user.first_name, "John")
        self.assertEqual(user.is_active, self.user.is_active)

    def test_update_last_name(self):
        response = self.client.post(reverse("accounts:profile"), {'first_name': self.user.first_name,
                                                                  'username': self.user.username,
                                                                  'email': self.user.email,
                                                                  'last_name': "Doe"})
        user = User.objects.get(id=self.user.id)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("accounts:profile"))
        self.assertEqual(user.last_name, "Doe")
        self.assertEqual(user.is_active, self.user.is_active)

    def test_update_email(self):
        response = self.client.post(reverse("accounts:profile"), {'first_name': self.user.first_name,
                                                                  'username': self.user.username,
                                                                  'email': "test@valid.com",
                                                                  'last_name': self.user.last_name})
        user = User.objects.get(id=self.user.id)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("accounts:profile"))
        self.assertEqual(user.email, "test@valid.com")
        self.assertEqual(user.is_active, self.user.is_active)

    def test_invalid_email(self):
        response = self.client.post(reverse("accounts:profile"), {'first_name': self.user.first_name,
                                                                  'username': self.user.username,
                                                                  'email': "test",
                                                                  'last_name': self.user.last_name})
        user = User.objects.get(id=self.user.id)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(user.email, self.user.email)
        self.assertEqual(user.is_active, self.user.is_active)


class ChangeUserPasswordViewTest(BasicAccountsTest):
    @classmethod
    def setUpTestData(cls):
        super(ChangeUserPasswordViewTest, cls).setUpTestData()

    def setUp(self):
        self.client = Client()
        self.client.login(username='test', password='nix')

    def test_valid_passwords(self):
        response = self.client.post(reverse("accounts:change_password"), {'old_password': "nix",
                                                                          'new_password1': "g(Zgm2g_*=/8%Pb,",
                                                                          'new_password2': "g(Zgm2g_*=/8%Pb,"})
        user = User.objects.get(id=self.user.id)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("accounts:change_password"))
        self.assertTrue(check_password("g(Zgm2g_*=/8%Pb,", user.password))

    def test_weak_new_password(self):
        response = self.client.post(reverse("accounts:change_password"), {'old_password': "nix",
                                                                          'new_password1': "password",
                                                                          'new_password2': "password"})
        user = User.objects.get(id=self.user.id)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(check_password("nix", user.password))

    def test_wrong_old_password(self):
        response = self.client.post(reverse("accounts:change_password"), {'old_password': "old password",
                                                                          'new_password1': "g(Zgm2g_*=/8%Pb,",
                                                                          'new_password2': "g(Zgm2g_*=/8%Pb,"})
        user = User.objects.get(id=self.user.id)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(check_password("nix", user.password))

    def test_unequal_passwords(self):
        response = self.client.post(reverse("accounts:change_password"), {'old_password': "nix",
                                                                          'new_password1': "g(Zgm2g_*=/8%Pb,",
                                                                          'new_password2': "g(Zgm2g_*=/8%Pb"})
        user = User.objects.get(id=self.user.id)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(check_password("nix", user.password))


class UserListViewTest(BasicAccountsTest):
    @classmethod
    def setUpTestData(cls):
        super(UserListViewTest, cls).setUpTestData()
        cls.group = Group.objects.create(name='User manager')

    def setUp(self):
        self.user.groups.add(self.group)
        self.client = Client()
        self.client.login(username='test', password='nix')
        self.user2 = User.objects.create_user(username="test2", email="temporary2@gmail.com", password='nix',
                                              first_name="Firstname", last_name="Surname")

    def test_listing(self):
        response = self.client.get(reverse("accounts:user_list"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context_data['object_list'].count(), 2)
        self.assertContains(response, self.user)
        self.assertContains(response, self.user2)


class UserEditViewTest(BasicAccountsTest):
    @classmethod
    def setUpTestData(cls):
        super(UserEditViewTest, cls).setUpTestData()
        cls.group = Group.objects.create(name='User manager')

    def setUp(self):
        self.user.groups.add(self.group)
        self.client = Client()
        self.client.login(username='test', password='nix')
        self.simple_user = User.objects.create_user(username="test2", email="temporary2@gmail.com", password='nix',
                                                    first_name="Firstname", last_name="Surname", is_active=False)

    def test_update_is_active(self):
        for state in [False, True]:
            with self.subTest(state=state):
                response = self.client.post(reverse("accounts:edit_user", args=[self.simple_user.id]),
                                            {'first_name': self.simple_user.first_name,
                                             'username': self.simple_user.username, 'email': self.simple_user.email,
                                             'last_name': self.simple_user.last_name, 'is_active': state})
                self.simple_user.refresh_from_db()
                self.assertEqual(response.status_code, 302)
                self.assertRedirects(response, reverse("accounts:user_list"))
                self.assertEqual(self.simple_user.is_active, state)

    def test_update_first_name(self):
        response = self.client.post(reverse("accounts:edit_user", args=[self.simple_user.id]),
                                    {'first_name': "John", 'username': self.simple_user.username,
                                     'email': self.simple_user.email, 'last_name': self.simple_user.last_name,
                                     'is_active': self.simple_user.is_active})
        user = User.objects.get(id=self.simple_user.id)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("accounts:user_list"))
        self.assertEqual(user.first_name, "John")

    def test_update_last_name(self):
        response = self.client.post(reverse("accounts:edit_user", args=[self.simple_user.id]),
                                    {'first_name': self.simple_user.first_name, 'username': self.simple_user.username,
                                     'email': self.simple_user.email, 'last_name': "Doe",
                                     'is_active': self.simple_user.is_active})
        user = User.objects.get(id=self.simple_user.id)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("accounts:user_list"))
        self.assertEqual(user.last_name, "Doe")

    def test_update_email(self):
        response = self.client.post(reverse("accounts:edit_user", args=[self.simple_user.id]),
                                    {'first_name': self.simple_user.first_name, 'username': self.simple_user.username,
                                     'email': "test@valid.com", 'last_name': self.simple_user.last_name,
                                     'is_active': self.simple_user.is_active})
        user = User.objects.get(id=self.simple_user.id)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("accounts:user_list"))
        self.assertEqual(user.email, "test@valid.com")

    def test_invalid_email(self):
        response = self.client.post(reverse("accounts:edit_user", args=[self.simple_user.id]),
                                    {'first_name': self.simple_user.first_name, 'username': self.simple_user.username,
                                     'email': "test", 'last_name': self.simple_user.last_name,
                                     'is_active': self.simple_user.is_active})
        user = User.objects.get(id=self.simple_user.id)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(user.email, self.simple_user.email)


class SetGroupsTest(BasicAccountsTest):
    @classmethod
    def setUpTestData(cls):
        super(SetGroupsTest, cls).setUpTestData()
        cls.group = Group.objects.create(name='User manager')
        cls.group2 = Group.objects.create(name='Annotator')
        cls.group3 = Group.objects.create(name='Trainer')

    def setUp(self):
        self.user.groups.add(self.group)
        self.client = Client()
        self.client.login(username='test', password='nix')
        self.user2 = User.objects.create_user(username="test2", email="temporary2@gmail.com", password='nix',
                                              first_name="Firstname", last_name="Surname")

    def test_edit_groups(self):
        # this will overwrite self.user's groups!
        response = self.client.post(reverse("accounts:set_groups"),
                                    {'checked[]': [self.group2.id], 'username': self.user.username},
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        user = User.objects.get(id=self.user.id)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(set([g.id for g in user.groups.all()]), {self.group2.id})

    def test_clear_groups(self):
        response = self.client.post(reverse("accounts:set_groups"), {'checked[]': [''], 'username': self.user.username},
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        user = User.objects.get(id=self.user.id)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(user.groups.all().count(), 0)

    def test_invalid_group(self):
        response = self.client.post(reverse("accounts:set_groups"), {'checked[]': [0],
                                                                     'username': self.user.username},
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        user = User.objects.get(id=self.user.id)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(user.groups.all().count(), 0)

    def test_insufficient_parameters(self):
        response = self.client.post(reverse("accounts:set_groups"), {'username': self.user.username},
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        user = User.objects.get(id=self.user.id)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(set([g.id for g in user.groups.all()]), {self.group.id})

        response = self.client.post(reverse("accounts:set_groups"), {'checked[]': [self.group2.id]},
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        user = User.objects.get(id=self.user.id)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(set([g.id for g in user.groups.all()]), {self.group.id})

        response = self.client.post(reverse("accounts:set_groups"), {'username': self.user.username,
                                                                     'checked[]': [self.group2.id]})
        user = User.objects.get(id=self.user.id)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(set([g.id for g in user.groups.all()]), {self.group.id})

    def test_get(self):
        response = self.client.get(reverse("accounts:set_groups"), HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 400)


class SetPasswordTest(BasicAccountsTest):
    @classmethod
    def setUpTestData(cls):
        super(SetPasswordTest, cls).setUpTestData()
        cls.group = Group.objects.create(name='User manager')

    def setUp(self):
        self.user.groups.add(self.group)
        self.client = Client()
        self.client.login(username='test', password='nix')

    def test_valid_password(self):
        response = self.client.post(reverse("accounts:set_user_password"), {'password1': "g(Zgm2g_*=/8%Pb,",
                                                                            'password2': "g(Zgm2g_*=/8%Pb,",
                                                                            'username': self.user.username},
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        user = User.objects.get(id=self.user.id)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(check_password("g(Zgm2g_*=/8%Pb,", user.password))

    def test_weak_password(self):
        response = self.client.post(reverse("accounts:set_user_password"), {'password1': "password",
                                                                            'password2': "password",
                                                                            'username': self.user.username},
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        user = User.objects.get(id=self.user.id)
        self.assertEqual(response.status_code, 400)
        self.assertTrue(check_password("nix", user.password))

    def test_unequal_passwords(self):
        response = self.client.post(reverse("accounts:set_user_password"), {'password1': "g(Zgm2g_*=/8%Pb,",
                                                                            'password2': "g(Zgm2g_*=/8%Pb",
                                                                            'username': self.user.username},
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        user = User.objects.get(id=self.user.id)
        self.assertEqual(response.status_code, 400)
        self.assertTrue(check_password("nix", user.password))

    def test_insufficient_parameters(self):
        response = self.client.post(reverse("accounts:set_user_password"), {'password2': "g(Zgm2g_*=/8%Pb",
                                                                            'username': self.user.username},
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        user = User.objects.get(id=self.user.id)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(set([g.id for g in user.groups.all()]), {self.group.id})

        response = self.client.post(reverse("accounts:set_user_password"), {'password1': "g(Zgm2g_*=/8%Pb,",
                                                                            'username': self.user.username},
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        user = User.objects.get(id=self.user.id)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(set([g.id for g in user.groups.all()]), {self.group.id})

        response = self.client.post(reverse("accounts:set_user_password"), {'password1': "g(Zgm2g_*=/8%Pb,",
                                                                            'password2': "g(Zgm2g_*=/8%Pb"},
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        user = User.objects.get(id=self.user.id)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(set([g.id for g in user.groups.all()]), {self.group.id})

        response = self.client.post(reverse("accounts:set_user_password"), {'password1': "g(Zgm2g_*=/8%Pb,",
                                                                            'password2': "g(Zgm2g_*=/8%Pb",
                                                                            'username': self.user.username})
        user = User.objects.get(id=self.user.id)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(set([g.id for g in user.groups.all()]), {self.group.id})

    def test_get(self):
        response = self.client.get(reverse("accounts:set_user_password"), HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 400)


class UserDeleteViewTest(BasicAccountsTest):
    @classmethod
    def setUpTestData(cls):
        super(UserDeleteViewTest, cls).setUpTestData()
        cls.group = Group.objects.create(name='User manager')

    def setUp(self):
        self.user.groups.add(self.group)
        self.client = Client()
        self.client.login(username='test', password='nix')
        self.simple_user = User.objects.create_user(username="test2", email="temporary2@gmail.com", password='nix',
                                                    first_name="Firstname", last_name="Surname", is_active=False)

    def test_delete_user_without_annotation(self):
        response = self.client.post(reverse("accounts:delete_user", args=[self.simple_user.id]))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("accounts:user_list"))
        self.assertFalse(User.objects.filter(id=self.simple_user.id).exists())

    def test_delete_user_with_annotation(self):
        classtype = Classtype.objects.create(name='Concept')
        klass = Class.objects.create(name='Test Concept', classtypeid=classtype)
        collection = Collection.objects.create(basepath="webcrawler", name="Webcrawler")
        image = Image.objects.create(collectionid=collection, path="path/to/image.jpg")
        Imageannotation.objects.create(difficult=False, groundtruth=True, classid=klass,
                                       imageid=image, userid=self.simple_user)
        response = self.client.post(reverse("accounts:delete_user", args=[self.simple_user.id]))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("accounts:user_list"))
        self.assertTrue(User.objects.filter(id=self.simple_user.id).exists())


class UserCreateViewTest(BasicAccountsTest):
    @classmethod
    def setUpTestData(cls):
        super(UserCreateViewTest, cls).setUpTestData()
        cls.group = Group.objects.create(name='User manager')

    def setUp(self):
        self.user.groups.add(self.group)
        self.client = Client()
        self.client.login(username='test', password='nix')

    def test_create_user(self):
        self.assertFalse(User.objects.filter(username="test2").exists())
        response = self.client.post(reverse("accounts:create_user"), {'first_name': "Jane", 'username': "test2",
                                                                      'email': "jane@gmail.com", 'last_name': "Doe-Roe",
                                                                      'password1': "g(Zgm2g_*=/8%Pb,",
                                                                      'password2': "g(Zgm2g_*=/8%Pb,"})
        self.assertTrue(User.objects.filter(username="test2").exists())
        user = User.objects.get(username="test2")
        self.assertEqual("Jane", user.first_name)
        self.assertEqual("Doe-Roe", user.last_name)
        self.assertEqual("jane@gmail.com", user.email)
        self.assertTrue(check_password("g(Zgm2g_*=/8%Pb,", user.password))
        self.assertTrue(user.is_active)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("accounts:user_list"))


class LoginViewTest(BasicAccountsTest):
    @classmethod
    def setUpTestData(cls):
        super(LoginViewTest, cls).setUpTestData()

    def setUp(self):
        self.client = Client()

    def test_valid_credentials(self):
        response = self.client.post(reverse("base:start"), {'username': "test", 'password': "nix"})
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("accounts:profile"))
        self.assertTrue(auth.get_user(self.client).is_authenticated)

    def test_invalid_credentials(self):
        response = self.client.post(reverse("base:start"), {'username': "test", 'password': "invalid"})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(auth.get_user(self.client).is_authenticated)

    def test_defense(self):
        # TODO is this feasible?
        pass
        # for i in range(3):
        #     response = self.client.post(reverse("base:start"), {'username': "test", 'password': "invalid"})
        #     self.assertEqual(response.status_code, 200)
        #     self.assertFalse(auth.get_user(self.client).is_authenticated)
        # response = self.client.post(reverse("base:start"), {'username': "test", 'password': "nix"})
        # self.assertEqual(response.status_code, 200)
        # self.assertFalse(auth.get_user(self.client).is_authenticated)


class UserApplyViewTest(BasicAccountsTest):
    @classmethod
    def setUpTestData(cls):
        super(UserApplyViewTest, cls).setUpTestData()
        cls.group = Group.objects.create(name='User manager')

    def setUp(self):
        self.user.groups.add(self.group)
        self.client = Client()
        self.client.login(username='test', password='nix')

    def test_create_user(self):
        self.assertFalse(User.objects.filter(username="test2").exists())
        response = self.client.post(reverse("accounts:apply_user"), {'first_name': "Jane", 'username': "test2",
                                                                     'email': "jane@gmail.com", 'last_name': "Doe-Roe",
                                                                     'password1': "g(Zgm2g_*=/8%Pb,",
                                                                     'password2': "g(Zgm2g_*=/8%Pb,"})
        self.assertTrue(User.objects.filter(username="test2").exists())
        user = User.objects.get(username="test2")
        self.assertEqual("Jane", user.first_name)
        self.assertEqual("Doe-Roe", user.last_name)
        self.assertEqual("jane@gmail.com", user.email)
        self.assertTrue(check_password("g(Zgm2g_*=/8%Pb,", user.password))
        self.assertFalse(user.is_active)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("base:start"))
