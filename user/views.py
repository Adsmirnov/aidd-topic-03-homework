from django.contrib.auth import authenticate, login, logout
from django.shortcuts import redirect, render
from django.views.generic import View

from .forms import AuthForm, RegistrationForm


class AuthView(View):
    """Авторизация"""

    @staticmethod
    def get(request):
        return render(request, "user/auth.html", {"form": AuthForm})

    @staticmethod
    def post(request):
        form = AuthForm(request.POST)
        user = None
        if form.is_valid():
            user = authenticate(
                request,
                username=form.cleaned_data["email"].lower(),
                password=form.cleaned_data["password"],
            )

        if user is not None:
            login(request, user)
            return redirect("dashboard:index")
        else:
            return render(
                request,
                "user/auth.html",
                {
                    "form": form,
                    "error": "Неверный логин или пароль! Повторите попытку.",
                },
            )


class RegistrationView(View):
    """Регистрация"""

    @staticmethod
    def get(request):
        return render(request, "user/registration.html", {"form": RegistrationForm})

    @staticmethod
    def post(request):
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("dashboard:index")
        else:
            errors = [error for errors in form.errors.values() for error in errors]
            return render(
                request,
                "user/registration.html",
                {"form": form, "error": " ".join(errors)},
            )


class LogoutView(View):
    """Выход"""

    @staticmethod
    def get(request):
        logout(request)
        return redirect("dashboard:index")
