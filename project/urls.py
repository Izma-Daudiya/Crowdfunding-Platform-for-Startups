"""
URL configuration for project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from pro import views
from django.conf.urls.static import static
from django.conf import settings
from django.views.defaults import page_not_found

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home),
    path('admin-dashboard', views.admin_dashboard),
    path('register', views.register),
    path('login', views.login),
    path('fetchregisterdata', views.fetchregisterdata),
    path('checklogindata', views.checklogindata),
    path('logout', views.logout),
    path('page404', views.page404),
    path('about', views.about),
    path('cart', views.cart),
    path('checkout', views.checkout),
    path('contact', views.contact),
    path('event-details', views.eventdetails),
    path('events', views.events),
    path('events-carousel', views.eventscarousel),
    path('events-list', views.eventslist),
    path('faqs', views.faqs),
    path('gallery', views.gallery),
    path('gallery-carousel', views.gallerycarousel),
    path('news', views.news),
    path('news-carousel', views.newscarousel),
    path('news-details', views.newsdetails),
    path('news-sidebar', views.newssidebar),
    path('partner', views.partner),
    path('product-details', views.productdetails),
    path('products', views.products),
    path('projects', views.projects),
    path('project-carousel', views.projectcarousel),
    path('projectdetails/<int:id>', views.projectdetails, name="projectdetails"),
    path('team', views.team),
    path('team-carousel', views.teamcarousel),
    path('testimonials', views.testimonials),
    path('testimonials-carousel', views.testimonialscarousel),
    path('userdetail', views.userdetail),
    path('startup', views.startup),
    path('fetchUserDetail', views.fetchUserDetail),
    path('user_validity', views.user_validity),
    path('startupDetail', views.startupDetail),
    path('startup_status', views.startup_status),
    path('documents', views.documents),
    path('documentDetails', views.documentDetails),
    path('project', views.project),
    path('project_status', views.project_status),
    path('projectDetails', views.projectDetails),
    path('wishlist', views.wishlist),
    path('toggle_wishlist/<int:project_id>/', views.toggle_wishlist, name='toggle_wishlist'),
    path('manage_campaign', views.manage_campaign),
    path('update', views.update),
    path('faq', views.faq),
    path('edit/<str:model_type>', views.edit),
    path('delete/<str:model_type>/<int:id>', views.delete),
    path('feedback', views.feedback),
    path('categorywiseproject/<int:id>', views.categorywiseproject),
    path('user_profile', views.user_profile),
    path('newsletter', views.newsletter),
    path('userdetail/<int:user_id>', views.userdetail, name='userdetail'),
    path('submitContact', views.submitContact),
    path('review', views.review),
    path('privacypolicy', views.privacypolicy),
    path('investment/<int:id>',views.investment),
    path('payment-success', views.payment_success),
    path('confirminvestment', views.confirminvestment),
    path('manageinvestment', views.manageinvestment),
    # path('admin/release_funds/<int:escrow_id>/', views.release_funds_to_entrepreneur, name='release_funds'),
    path('search-redirect/', views.search_redirect, name='search_redirect'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    urlpatterns += [
        path('404-test', page_not_found, {'exception': None}, name='404_test'),
    ]