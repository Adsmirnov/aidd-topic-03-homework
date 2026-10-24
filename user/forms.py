from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from user.models import User

INPUT_CLASS = "form-control my-3 p-4"


def email_field():
    return forms.EmailField(
        widget=forms.EmailInput(attrs={"class": INPUT_CLASS, "placeholder": "Email"})
    )


def password_field(placeholder):
    return forms.CharField(
        widget=forms.PasswordInput(
            attrs={"class": INPUT_CLASS, "placeholder": placeholder}
        )
    )


class RegistrationForm(forms.Form):
    """Форма регистрации пользователей"""

    email = email_field()
    password1 = password_field("Пароль")
    password2 = password_field("Повторите пароль")

    def clean_email(self):
        # Login lowercases the email, so it is stored lowercased as well
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError(
                "Данный e-mail уже зарегистрирован! Введите другой e-mail или"
                " воспользуйтесь формой авторизации."
            )
        return email

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise ValidationError("Введенные пароли не совпадают")
        if password1:
            email = cleaned_data.get("email")
            validate_password(password1, User(username=email, email=email))
        return cleaned_data

    def save(self):
        email = self.cleaned_data["email"]
        password = self.cleaned_data["password1"]
        User.objects.create_user(email, email, password)
        return authenticate(username=email, password=password)


class AuthForm(forms.Form):
    """Форма авторизации пользователей"""

    email = email_field()
    password = password_field("Пароль")

    def get_user(self, request):
        """The authenticated user, or None if the form or credentials are invalid."""
        if not self.is_valid():
            return None
        return authenticate(
            request,
            username=self.cleaned_data["email"].lower(),
            password=self.cleaned_data["password"],
        )
