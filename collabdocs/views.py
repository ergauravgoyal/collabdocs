from django.db import IntegrityError, transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_datetime
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import AuditLog, Comment, Document, DocumentVersion, Tag, User, Workspace, WorkspaceMember
from .serializers import (
    AuditLogSerializer,
    CommentSerializer,
    DocumentSerializer,
    DocumentVersionSerializer,
    TagSerializer,
    UserSerializer,
    WorkspaceMemberSerializer,
    WorkspaceSerializer,
)


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    http_method_names = ["get", "post", "head", "options"]


class WorkspaceViewSet(viewsets.ModelViewSet):
    serializer_class = WorkspaceSerializer

    def get_queryset(self):
        return Workspace.objects.select_related("owner").annotate(member_count=Count("members"))

    @transaction.atomic
    def perform_create(self, serializer):
        workspace = serializer.save()
        WorkspaceMember.objects.create(
            workspace=workspace, user=workspace.owner, role=WorkspaceMember.Role.ADMIN
        )

    @action(detail=True, methods=["post"])
    def members(self, request, pk=None):
        workspace = self.get_object()
        serializer = WorkspaceMemberSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                member = WorkspaceMember.objects.create(
                    workspace=workspace, user_id=serializer.validated_data["user_id"],
                    role=serializer.validated_data["role"],
                )
        except IntegrityError as exc:
            return Response(
                {"detail": "This user is already a workspace member."},
                status=status.HTTP_409_CONFLICT,
            )
        return Response(WorkspaceMemberSerializer(member).data, status=status.HTTP_201_CREATED)

    @members.mapping.get
    def list_members(self, request, pk=None):
        members = WorkspaceMember.objects.filter(workspace_id=pk).select_related("user")
        return Response(WorkspaceMemberSerializer(members, many=True).data)

    @action(detail=True, methods=["get"])
    def summary(self, request, pk=None):
        workspace = self.get_queryset().get(pk=pk)
        summary = Workspace.objects.filter(pk=workspace.pk).aggregate(
            document_count=Count("documents", distinct=True),
            member_count=Count("members", distinct=True),
            comment_count=Count("documents__comments", distinct=True),
        )
        return Response(summary)


class DocumentViewSet(viewsets.ModelViewSet):
    serializer_class = DocumentSerializer

    def get_queryset(self):
        queryset = (
            Document.objects.select_related("workspace", "created_by")
            .prefetch_related("tags", "versions", "comments")
            .annotate(comment_count=Count("comments", distinct=True))
        )
        params = self.request.query_params
        if params.get("workspace"):
            queryset = queryset.filter(workspace_id=params["workspace"])
        if params.get("status"):
            queryset = queryset.filter(status__in=params["status"].split(","))
        if params.get("tag"):
            queryset = queryset.filter(tags__name=params["tag"])
        if params.get("search"):
            term = params["search"]
            queryset = queryset.filter(Q(title__icontains=term) | Q(content__icontains=term))
        if params.get("updated_after") and parse_datetime(params["updated_after"]):
            queryset = queryset.filter(updated_at__gte=parse_datetime(params["updated_after"]))
        if params.get("updated_before") and parse_datetime(params["updated_before"]):
            queryset = queryset.filter(updated_at__lte=parse_datetime(params["updated_before"]))
        return queryset.distinct()

    @transaction.atomic
    def perform_create(self, serializer):
        document = serializer.save()
        DocumentVersion.objects.create(
            document=document, content=document.content, version_number=document.versions.count() + 1,
            saved_by=document.created_by,
        )

    @transaction.atomic
    def perform_update(self, serializer):
        document = serializer.save()
        DocumentVersion.objects.create(
            document=document, content=document.content, version_number=document.versions.count() + 1,
            saved_by=self.request.user if self.request.user.is_authenticated else document.created_by,
        )

    @action(detail=True, methods=["get"])
    def versions(self, request, pk=None):
        versions = DocumentVersion.objects.filter(document_id=pk).select_related("saved_by").order_by("version_number")
        return Response(DocumentVersionSerializer(versions, many=True).data)

    @action(detail=True, methods=["get"])
    def stats(self, request, pk=None):
        document = self.get_object()
        stats = Document.objects.filter(pk=document.pk).aggregate(
            version_count=Count("versions", distinct=True),
            comment_count=Count("comments", distinct=True),
            contributor_count=Count("comments__author", distinct=True),
        )
        return Response(stats)

    @action(detail=True, methods=["post"])
    def tags(self, request, pk=None):
        document = self.get_object()
        tag_ids = request.data.get("tag_ids", [])
        if not isinstance(tag_ids, list):
            return Response({"detail": "tag_ids must be a list."}, status=status.HTTP_400_BAD_REQUEST)
        tags = Tag.objects.filter(id__in=tag_ids)
        document.tags.add(*tags)
        return Response(TagSerializer(tags, many=True).data)


class CommentViewSet(viewsets.ModelViewSet):
    serializer_class = CommentSerializer

    def get_queryset(self):
        queryset = Comment.objects.select_related("author", "document", "parent")
        if self.request.query_params.get("document"):
            queryset = queryset.filter(document_id=self.request.query_params["document"])
        return queryset

    def perform_create(self, serializer):
        serializer.save(author=self.request.user if self.request.user.is_authenticated else None)


class TagViewSet(viewsets.ModelViewSet):
    serializer_class = TagSerializer

    def get_queryset(self):
        return Tag.objects.annotate(document_count=Count("documents"))


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AuditLogSerializer

    def get_queryset(self):
        queryset = AuditLog.objects.select_related("actor").all()
        if self.request.query_params.get("actor"):
            queryset = queryset.filter(actor_id=self.request.query_params["actor"])
        if self.request.query_params.get("from"):
            queryset = queryset.filter(timestamp__gte=self.request.query_params["from"])
        if self.request.query_params.get("to"):
            queryset = queryset.filter(timestamp__lte=self.request.query_params["to"])
        return queryset
