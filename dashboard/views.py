from django.contrib.auth.mixins import UserPassesTestMixin
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from .forms import ShareModelForm
from .models import Share
from .services.graph import get_graph


class IsUserAuthenticatedMixin(UserPassesTestMixin):
    """Only logged in users; guests are sent to the share list."""

    def test_func(self):
        return self.request.user.is_authenticated

    def handle_no_permission(self):
        return redirect("dashboard:index")


class ShareListView(ListView):
    """Список акций"""

    model = Share
    template_name = "dashboard/list.html"
    paginate_by = 100
    ordering = ["name"]


class ShareDetailView(DetailView):
    """Карточка акции с графиком"""

    model = Share
    template_name = "dashboard/detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["plot_div"] = get_graph(self.object)
        return context


class ShareFormMixin(IsUserAuthenticatedMixin):
    model = Share
    template_name = "dashboard/create.html"
    form_class = ShareModelForm
    success_url = reverse_lazy("dashboard:index")


class ShareCreateView(ShareFormMixin, CreateView):
    """Добавление инструмента"""


class ShareUpdateView(ShareFormMixin, UpdateView):
    """Редактирование инструмента"""


class ShareDeleteView(IsUserAuthenticatedMixin, DeleteView):
    """Удаление инструмента"""

    model = Share
    template_name = "dashboard/delete.html"
    success_url = reverse_lazy("dashboard:index")
