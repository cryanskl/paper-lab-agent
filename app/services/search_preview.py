from typing import Literal


RollbackAction = Literal["remove", "preserve_saved", "preserve_preview"]


def decide_rollback_action(
    *,
    has_document: bool,
    has_other_saved_search: bool,
    has_other_preview_search: bool,
) -> RollbackAction:
    """Choose what happens to one newly discovered paper when its search is undone.

    A saved paper remains in the normal local library. A preview paper remains
    visible only inside another undecided search batch.
    """
    if has_document or has_other_saved_search:
        return "preserve_saved"
    if has_other_preview_search:
        return "preserve_preview"
    return "remove"
