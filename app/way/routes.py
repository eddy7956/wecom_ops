from flask import Blueprint, jsonify
from app.way.service import sync_contact_way
bp = Blueprint("way", __name__)
@bp.route("/sync", methods=["POST"])
def sync_way():
    return jsonify(sync_contact_way())
