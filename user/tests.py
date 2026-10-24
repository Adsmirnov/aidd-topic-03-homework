from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

User = get_user_model()

STRONG_PASSWORD = "Kv8!pq2Lmz"


class RegistrationTests(TestCase):
    def register(self, email, password1=STRONG_PASSWORD, password2=None):
        return self.client.post(
            reverse("user:registration"),
            {
                "email": email,
                "password1": password1,
                "password2": password2 or password1,
            },
        )

    def test_registration_logs_user_in(self):
        """ФТ-10, ФТ-13."""
        response = self.register("new@mail.ru")
        self.assertRedirects(response, reverse("dashboard:index"))
        self.assertTrue(User.objects.filter(email="new@mail.ru").exists())
        self.assertIn("_auth_user_id", self.client.session)

    def test_passwords_must_match(self):
        """ФТ-11."""
        response = self.register("new@mail.ru", STRONG_PASSWORD, STRONG_PASSWORD + "x")
        self.assertContains(response, "Введенные пароли не совпадают")
        self.assertFalse(User.objects.exists())

    def test_email_must_be_unique(self):
        """ФТ-12."""
        self.register("new@mail.ru")
        self.client.logout()
        response = self.register("new@mail.ru")
        self.assertContains(response, "Данный e-mail уже зарегистрирован")

    def test_email_is_case_insensitive(self):
        """Д-15: User@Mail.ru could register but never log in."""
        self.register("User@Mail.ru")
        self.client.logout()
        response = self.client.post(
            reverse("user:auth"), {"email": "User@Mail.ru", "password": STRONG_PASSWORD}
        )
        self.assertRedirects(response, reverse("dashboard:index"))
        self.client.logout()
        response = self.register("user@mail.ru")
        self.assertContains(response, "Данный e-mail уже зарегистрирован")

    def test_invalid_email_shows_error(self):
        """Д-16: an invalid email gave 500."""
        response = self.register("not-an-email")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.exists())

    def test_weak_password_is_rejected(self):
        """Д-18: password validators were not applied."""
        response = self.register("new@mail.ru", "1")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.exists())


class AuthTests(TestCase):
    def setUp(self):
        User.objects.create_user("user@mail.ru", "user@mail.ru", STRONG_PASSWORD)

    def test_login_and_logout(self):
        """ФТ-14, ФТ-16."""
        response = self.client.post(
            reverse("user:auth"), {"email": "user@mail.ru", "password": STRONG_PASSWORD}
        )
        self.assertRedirects(response, reverse("dashboard:index"))
        response = self.client.get(reverse("dashboard:index"))
        self.assertContains(response, "Привет, user@mail.ru")
        self.client.get(reverse("user:logout"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_wrong_password(self):
        """ФТ-14."""
        response = self.client.post(
            reverse("user:auth"), {"email": "user@mail.ru", "password": "wrong"}
        )
        self.assertContains(response, "Неверный логин или пароль")

    def test_missing_field_is_not_500(self):
        """Д-17: a POST without the password field gave 500."""
        response = self.client.post(reverse("user:auth"), {"email": "user@mail.ru"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Неверный логин или пароль")

    def test_login_urls_have_slash(self):
        """Д-5."""
        self.assertEqual(reverse("user:auth"), "/user/login/")
