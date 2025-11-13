from flask import Blueprint, jsonify
from app.group.service import sync_groupchats
bp = Blueprint("group", __name__)
@bp.route("/sync", methods=["POST"])
def sync_group():
    return jsonify(sync_groupchats())
