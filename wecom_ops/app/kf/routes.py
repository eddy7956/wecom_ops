from flask import Blueprint, jsonify
from app.kf.service import sync_kf_accounts, sync_kf_servicers
bp = Blueprint("kf", __name__)
@bp.route("/sync", methods=["POST"])
def sync_kf():
    a = sync_kf_accounts(); s = sync_kf_servicers()
    return jsonify({**a, **s})
