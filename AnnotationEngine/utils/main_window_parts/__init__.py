"""Helpers for keeping `MainWindow` focused on orchestration."""

from .automask_handlers import (
    on_automask_all_requested,
    on_autoseg_cancelled,
    on_autoseg_error,
    on_autoseg_requested,
    on_autoseg_result,
    on_autoseg_worker_finished,
)
from .autoseg_yolo_handlers import (
    on_autoseg_yolo_cancelled,
    on_autoseg_yolo_error,
    on_autoseg_yolo_finished,
    on_autoseg_yolo_result,
    on_autoseg_yolo_run,
)
from .dirty_state import clear_unsaved, handle_close_event, on_data_changed
from .load_process import (
    load_process,
    on_folder_opened,
    on_image_load_requested,
    on_image_loaded,
    on_save_before_switch,
    on_visual_settings_applied,
)
from .auth_handlers import (
    on_auth_cancelled,
    on_auth_error,
    on_auth_finished,
    on_auth_requested,
    on_auth_success,
)
from .collab_payload import (
    build_collab_annotation_payload,
    is_empty_mask_annotation,
    normalize_collab_annotation_payload,
)
from .collab_handlers import (
    emit_collab_annotation,
    flush_pending_mask_updates,
    load_collab_image_event,
    load_collab_snapshot_image,
    on_chat_requested,
    on_collab_annotation_added,
    on_collab_annotation_removed,
    on_collab_annotation_updated,
    on_collab_event_received,
    on_collab_snapshot_received,
    schedule_mask_update_emit,
    sync_collab_current_image_if_needed,
)

__all__ = [
    "clear_unsaved",
    "handle_close_event",
    "load_process",
    "on_automask_all_requested",
    "on_autoseg_cancelled",
    "on_autoseg_error",
    "on_autoseg_requested",
    "on_autoseg_result",
    "on_autoseg_worker_finished",
    "on_autoseg_yolo_cancelled",
    "on_autoseg_yolo_error",
    "on_autoseg_yolo_finished",
    "on_autoseg_yolo_result",
    "on_autoseg_yolo_run",
    "on_data_changed",
    "on_folder_opened",
    "on_image_load_requested",
    "on_image_loaded",
    "on_save_before_switch",
    "on_visual_settings_applied",
    "on_auth_cancelled",
    "on_auth_error",
    "on_auth_finished",
    "on_auth_requested",
    "on_auth_success",
    "build_collab_annotation_payload",
    "is_empty_mask_annotation",
    "normalize_collab_annotation_payload",
    "emit_collab_annotation",
    "flush_pending_mask_updates",
    "load_collab_image_event",
    "load_collab_snapshot_image",
    "on_chat_requested",
    "on_collab_annotation_added",
    "on_collab_annotation_removed",
    "on_collab_annotation_updated",
    "on_collab_event_received",
    "on_collab_snapshot_received",
    "schedule_mask_update_emit",
    "sync_collab_current_image_if_needed",
]

