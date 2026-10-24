from django.contrib.auth import login, logout
from django.shortcuts import redirect, render
from django.views.generic import View

from .forms import AuthForm, RegistrationForm


class AuthView(View):
    """Авторизация"""

    template_name = "user/auth.html"

    def get(self, request):
        return render(request, self.template_name, {"form": AuthForm()})

    def post(self, request):
        form = AuthForm(request.POST)
        user = form.get_user(request)
        if user is None:
            return render(
                request,
                self.template_name,
                {"form": form, "error": "Неверный логин или пароль! Повторите попытку."},
            )
        login(request, user)
        return redirect("dashboard:index")


class RegistrationView(View):
    """Регистрация"""

    template_name = "user/registration.html"

    def get(self, request):
        return render(request, self.template_name, {"form": RegistrationForm()})

    def post(self, request):
        form = RegistrationForm(request.POST)
        if not form.is_valid():
            errors = [error for errors in form.errors.values() for error in errors]
            return render(
                request, self.template_name, {"form": form, "error": " ".join(errors)}
            )
        login(request, form.save())
        return redirect("dashboard:index")


class LogoutView(View):
    """Выход"""

    def get(self, request):
        logout(request)
        return redirect("dashboard:index")
