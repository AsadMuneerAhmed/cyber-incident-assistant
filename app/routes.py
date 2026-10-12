
from flask import Blueprint, request, jsonify, render_template
from .database import get_db_connection
from .ai import analyze_incident


main = Blueprint("main", __name__)

@main.route("/")
def home():
    return render_template("index.html")

# Create and analyze a new incident
@main.route("/api/incidents", methods=["POST"])
def create_incident():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "error": "A valid JSON object is required."
        }), 400

    title = data.get("title")
    description = data.get("description")
    source_ip = data.get("source_ip")

    if not isinstance(title, str) or not title.strip():
        return jsonify({
            "error": "Title is required."
        }), 400

    if not isinstance(description, str) or not description.strip():
        return jsonify({
            "error": "Description is required."
        }), 400

    title = title.strip()
    description = description.strip()

    # Analyze the incident using Gemini
    analysis = analyze_incident(
        title,
        description,
        source_ip
    )

    connection = get_db_connection()

    try:
        cursor = connection.execute(
            """
            INSERT INTO incidents (
                title,
                description,
                source_ip,
                attack_type,
                severity,
                confidence,
                ai_analysis,
                recommendations
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                title,
                description,
                source_ip,
                analysis["attack_type"],
                analysis["severity"],
                analysis["confidence"],
                analysis["ai_analysis"],
                "\n".join(
                    str(item)
                    for item in analysis["recommendations"]
                ),
            )
        )

        connection.commit()
        incident_id = cursor.lastrowid

    finally:
        connection.close()

    return jsonify({
        "message": "Incident created and analyzed.",
        "incident_id": incident_id,
        "analysis": analysis
    }), 201

# Retrieve all incidents
@main.route("/api/incidents", methods=["GET"])
def get_incidents():
    connection = get_db_connection()

    try:
        incidents = connection.execute(
            """
            SELECT *
            FROM incidents
            ORDER BY created_at DESC
            """
        ).fetchall()

        results = [
            dict(incident)
            for incident in incidents
        ]

    finally:
        connection.close()

    return jsonify(results), 200


# Update an incident's status
@main.route("/api/incidents/<int:incident_id>/status", methods=["PATCH"])
def update_incident_status(incident_id):
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "error": "A valid JSON object is required."
        }), 400

    status = data.get("status")

    if status not in ["Open", "Closed"]:
        return jsonify({
            "error": "Status must be Open or Closed."
        }), 400

    connection = get_db_connection()

    try:
        incident = connection.execute(
            "SELECT id FROM incidents WHERE id = ?",
            (incident_id,)
        ).fetchone()

        if incident is None:
            return jsonify({
                "error": "Incident not found."
            }), 404

        connection.execute(
            """
            UPDATE incidents
            SET status = ?
            WHERE id = ?
            """,
            (status, incident_id)
        )

        connection.commit()

    finally:
        connection.close()

    return jsonify({
        "message": "Incident status updated.",
        "incident_id": incident_id,
        "status": status
    }), 200

# Delete an incident
@main.route("/api/incidents/<int:incident_id>", methods=["DELETE"])
def delete_incident(incident_id):
    connection = get_db_connection()

    try:
        incident = connection.execute(
            "SELECT id FROM incidents WHERE id = ?",
            (incident_id,)
        ).fetchone()

        if incident is None:
            return jsonify({
                "error": "Incident not found."
            }), 404

        connection.execute(
            "DELETE FROM incidents WHERE id = ?",
            (incident_id,)
        )

        connection.commit()

    finally:
        connection.close()

    return jsonify({
        "message": "Incident deleted.",
        "incident_id": incident_id
    }), 200
# Update an incident
@main.route("/api/incidents/<int:incident_id>", methods=["PUT"])
def update_incident(incident_id):
    data = request.get_json()

    if not data:
        return jsonify({
            "error": "No data provided."
        }), 400

    title = data.get("title")
    description = data.get("description")
    source_ip = data.get("source_ip")

    if not title or not description:
        return jsonify({
            "error": "Title and description are required."
        }), 400

    connection = get_db_connection()

    try:
        incident = connection.execute(
            "SELECT id FROM incidents WHERE id = ?",
            (incident_id,)
        ).fetchone()

        if incident is None:
            return jsonify({
                "error": "Incident not found."
            }), 404

        connection.execute(
            """
            UPDATE incidents
            SET title = ?, description = ?, source_ip = ?
            WHERE id = ?
            """,
            (title, description, source_ip, incident_id)
        )

        connection.commit()

    finally:
        connection.close()

    return jsonify({
        "message": "Incident updated.",
        "incident_id": incident_id
    }), 200