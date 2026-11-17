from django.db import IntegrityError
from rest_framework import serializers

from .models import (
    AuditLog,
    Comment,
    Document,
    DocumentVersion,
    Tag,
    User,
    Workspace,
    WorkspaceMember,
)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "first_name", "last_name", "email", "phone", "created_at"]
        read_only_fields = ["id", "created_at"]

    def validate_email(self, value):
        if "@" not in value:
            raise serializers.ValidationError("Enter a valid email address.")
        return value.lower()


class WorkspaceMemberSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    user_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = WorkspaceMember
        fields = ["id", "workspace", "user", "user_id", "role", "joined_at"]
        read_only_fields = ["id", "workspace", "joined_at"]

    def validate_role(self, value):
        if value not in WorkspaceMember.Role.values:
            raise serializers.ValidationError("Role must be admin, editor, or viewer.")
        return value

    def create(self, validated_data):
        try:
            return WorkspaceMember.objects.create(**validated_data)
        except IntegrityError as exc:
            raise serializers.ValidationError(
                {"detail": "This user is already a workspace member."}
            ) from exc


class WorkspaceSerializer(serializers.ModelSerializer):
    owner = UserSerializer(read_only=True)
    owner_id = serializers.UUIDField(write_only=True, required=False)
    member_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Workspace
        fields = ["id", "name", "owner", "owner_id", "is_active", "created_at", "member_count"]
        read_only_fields = ["id", "owner", "created_at", "member_count"]

    def validate_name(self, value):
        if not value.strip():
            raise serializers.ValidationError("Workspace name cannot be blank.")
        return value.strip()

    def create(self, validated_data):
        owner_id = validated_data.pop("owner_id", None)
        request = self.context.get("request")
        owner = request.user if request and request.user.is_authenticated else None
        if owner is None and owner_id:
            owner = User.objects.filter(id=owner_id).first()
        if owner is None:
            raise serializers.ValidationError(
                {"owner_id": "Provide a valid owner_id when authentication is not enabled."}
            )
        return Workspace.objects.create(owner=owner, **validated_data)


class DocumentVersionSerializer(serializers.ModelSerializer):
    saved_by = UserSerializer(read_only=True)

    class Meta:
        model = DocumentVersion
        fields = ["id", "document", "content", "version_number", "saved_by", "saved_at"]


class TagSerializer(serializers.ModelSerializer):
    document_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Tag
        fields = ["id", "name", "document_count"]
        read_only_fields = ["id", "document_count"]

    def validate_name(self, value):
        value = value.strip().lower()
        if not value:
            raise serializers.ValidationError("Tag name cannot be blank.")
        return value


class DocumentSerializer(serializers.ModelSerializer):
    created_by = UserSerializer(read_only=True)
    created_by_id = serializers.UUIDField(write_only=True, required=False)
    workspace_name = serializers.CharField(source="workspace.name", read_only=True)
    tag_names = serializers.SerializerMethodField()
    latest_version = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = [
            "id", "title", "content", "workspace", "workspace_name", "created_by", "created_by_id",
            "status", "updated_at", "tag_names", "latest_version",
        ]
        read_only_fields = ["id", "created_by", "updated_at", "workspace_name"]

    def get_tag_names(self, obj):
        return [tag.name for tag in obj.tags.all()]

    def get_latest_version(self, obj):
        version = obj.versions.order_by("-version_number").first()
        return version.version_number if version else None

    def validate_title(self, value):
        if not value.strip():
            raise serializers.ValidationError("Document title cannot be blank.")
        return value.strip()

    def create(self, validated_data):
        created_by_id = validated_data.pop("created_by_id", None)
        request = self.context.get("request")
        created_by = request.user if request and request.user.is_authenticated else None
        if created_by is None and created_by_id:
            created_by = User.objects.filter(id=created_by_id).first()
        if created_by is None:
            raise serializers.ValidationError(
                {"created_by_id": "Provide a valid created_by_id when authentication is not enabled."}
            )
        return Document.objects.create(created_by=created_by, **validated_data)


class CommentSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    reply_count = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = ["id", "document", "author", "content", "parent", "created_at", "reply_count"]
        read_only_fields = ["id", "author", "created_at", "reply_count"]

    def get_reply_count(self, obj):
        return obj.replies.count()

    def validate(self, attrs):
        parent = attrs.get("parent")
        document = attrs.get("document")
        if parent and parent.document_id != document.id:
            raise serializers.ValidationError(
                {"parent": "A reply must belong to the same document."}
            )
        return attrs


class AuditLogSerializer(serializers.ModelSerializer):
    actor = UserSerializer(read_only=True)

    class Meta:
        model = AuditLog
        fields = ["id", "actor", "action", "model_name", "object_id", "timestamp"]
