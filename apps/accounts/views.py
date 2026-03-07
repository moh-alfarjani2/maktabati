from django.views.generic import ListView, CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import CustomUser, Role
from apps.accounts.decorators import role_required
from django.utils.decorators import method_decorator

@method_decorator(role_required(allowed_roles=['admin']), name='dispatch')
class UserListView(LoginRequiredMixin, ListView):
    model = CustomUser
    template_name = 'accounts/user_list.html'
    context_object_name = 'users'
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset().select_related('role')
        sort = self.request.GET.get('sort')
        direction = self.request.GET.get('dir', 'desc')

        if sort:
            valid_sorts = ['username', 'first_name', 'email', 'role__name', 'is_active', 'date_joined']
            if sort in valid_sorts:
                if direction == 'desc':
                    sort = f"-{sort}"
                queryset = queryset.order_by(sort)
        else:
            queryset = queryset.order_by('-date_joined')

        return queryset

@method_decorator(role_required(allowed_roles=['admin']), name='dispatch')
class UserCreateView(LoginRequiredMixin, CreateView):
    model = CustomUser
    template_name = 'accounts/user_form.html'
    fields = ['username', 'first_name', 'last_name', 'email', 'role', 'is_active', 'password']
    success_url = reverse_lazy('user_list')
    
    def form_valid(self, form):
        user = form.save(commit=False)
        user.set_password(form.cleaned_data['password'])
        user.save()
        from django.http import HttpResponseRedirect
        return HttpResponseRedirect(self.success_url)

@method_decorator(role_required(allowed_roles=['admin']), name='dispatch')
class RoleListView(LoginRequiredMixin, ListView):
    model = Role
    template_name = 'accounts/role_list.html'
    context_object_name = 'roles'

@method_decorator(role_required(allowed_roles=['admin']), name='dispatch')
class RoleCreateView(LoginRequiredMixin, CreateView):
    model = Role
    template_name = 'accounts/role_form.html'
    fields = ['name']
    success_url = reverse_lazy('role_list')
@method_decorator(login_required, name='dispatch')
class UserProfileView(LoginRequiredMixin, UpdateView):
    model = CustomUser
    template_name = 'accounts/profile.html'
    fields = ['full_name', 'email', 'phone']
    success_url = reverse_lazy('profile')

    def get_object(self, queryset=None):
        return self.request.user

    def form_valid(self, form):
        messages.success(self.request, "تم تحديث ملفك الشخصي بنجاح.")
        return super().form_valid(form)
