from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.routers import DefaultRouter

from collabdocs.views import (
    AuditLogViewSet,
    CommentViewSet,
    DocumentViewSet,
    TagViewSet,
    UserViewSet,
    WorkspaceViewSet,
)

router = DefaultRouter()
router.register("users", UserViewSet, basename="user")
router.register("workspaces", WorkspaceViewSet, basename="workspace")
router.register("documents", DocumentViewSet, basename="document")
router.register("comments", CommentViewSet, basename="comment")
router.register("tags", TagViewSet, basename="tag")
router.register("audit-logs", AuditLogViewSet, basename="audit-log")

urlpatterns = [
    path("api/", include(router.urls)),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
]
