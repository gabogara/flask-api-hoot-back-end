from flask import Blueprint, jsonify, request, g
import psycopg2.extras

from auth_middleware import token_required
from db_helpers import get_db_connection, consolidate_comments_in_hoots

hoots_blueprint = Blueprint("hoots_blueprint", __name__)


@hoots_blueprint.route("/hoots", methods=["POST"])
@token_required
def create_hoot():
    connection = get_db_connection()
    try:
        new_hoot = request.get_json()
        author_id = g.user["id"]

        cursor = connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        cursor.execute(
            """
            INSERT INTO hoots (author, title, text, category)
            VALUES (%s, %s, %s, %s)
            RETURNING id
            """,
            (author_id, new_hoot["title"], new_hoot["text"], new_hoot["category"]),
        )
        hoot_id = cursor.fetchone()["id"]

        cursor.execute(
            """
            SELECT h.id,
                   h.author AS hoot_author_id,
                   h.title,
                   h.text,
                   h.category,
                   h.created_at AS "createdAt",
                   u_hoot.username AS author_username
            FROM hoots h
            JOIN users u_hoot ON h.author = u_hoot.id
            WHERE h.id = %s
            """,
            (hoot_id,),
        )
        created_hoot = cursor.fetchone()

        connection.commit()
        return jsonify(created_hoot), 201

    except Exception as error:
        connection.rollback()
        return jsonify({"error": str(error)}), 500
    finally:
        connection.close()


@hoots_blueprint.route("/hoots", methods=["GET"])
def hoots_index():
    connection = get_db_connection()
    try:
        cursor = connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute(
            """
            SELECT h.id,
                   h.author AS hoot_author_id,
                   h.title,
                   h.text,
                   h.category,
                   h.created_at AS "createdAt",
                   u_hoot.username AS author_username,
                   c.id AS comment_id,
                   c.text AS comment_text,
                   c.created_at AS "commentCreatedAt",
                   u_comment.username AS comment_author_username
            FROM hoots h
            INNER JOIN users u_hoot ON h.author = u_hoot.id
            LEFT JOIN comments c ON h.id = c.hoot
            LEFT JOIN users u_comment ON c.author = u_comment.id
            ORDER BY h.created_at DESC, c.created_at ASC
            """
        )
        hoots = cursor.fetchall()

        consolidated_hoots = consolidate_comments_in_hoots(hoots)
        return jsonify(consolidated_hoots), 200

    except Exception as error:
        return jsonify({"error": str(error)}), 500
    finally:
        connection.close()


@hoots_blueprint.route("/hoots/<int:hoot_id>", methods=["GET"])
def show_hoot(hoot_id):
    connection = get_db_connection()
    try:
        cursor = connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute(
            """
            SELECT h.id,
                   h.author AS hoot_author_id,
                   h.title,
                   h.text,
                   h.category,
                   h.created_at AS "createdAt",
                   u_hoot.username AS author_username,
                   c.id AS comment_id,
                   c.text AS comment_text,
                   c.created_at AS "commentCreatedAt",
                   u_comment.username AS comment_author_username
            FROM hoots h
            INNER JOIN users u_hoot ON h.author = u_hoot.id
            LEFT JOIN comments c ON h.id = c.hoot
            LEFT JOIN users u_comment ON c.author = u_comment.id
            WHERE h.id = %s
            """,
            (hoot_id,),
        )

        unprocessed_hoot = cursor.fetchall()
        if not unprocessed_hoot:
            return jsonify({"error": "Hoot not found"}), 404

        processed_hoot = consolidate_comments_in_hoots(unprocessed_hoot)[0]
        return jsonify(processed_hoot), 200

    except Exception as error:
        return jsonify({"error": str(error)}), 500
    finally:
        connection.close()


@hoots_blueprint.route("/hoots/<int:hoot_id>", methods=["PUT"])
@token_required
def update_hoot(hoot_id):
    connection = get_db_connection()
    try:
        updated_hoot_data = request.get_json()
        cursor = connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        cursor.execute("SELECT * FROM hoots WHERE id = %s", (hoot_id,))
        hoot_to_update = cursor.fetchone()
        if hoot_to_update is None:
            return jsonify({"error": "Hoot not found"}), 404

        if hoot_to_update["author"] != g.user["id"]:
            return jsonify({"error": "Unauthorized"}), 401

        cursor.execute(
            """
            UPDATE hoots
            SET title = %s, text = %s, category = %s
            WHERE id = %s
            RETURNING id
            """,
            (updated_hoot_data["title"], updated_hoot_data["text"], updated_hoot_data["category"], hoot_id),
        )
        updated_id = cursor.fetchone()["id"]

        cursor.execute(
            """
            SELECT h.id,
                   h.author AS hoot_author_id,
                   h.title,
                   h.text,
                   h.category,
                   h.created_at AS "createdAt",
                   u_hoot.username AS author_username
            FROM hoots h
            JOIN users u_hoot ON h.author = u_hoot.id
            WHERE h.id = %s
            """,
            (updated_id,),
        )
        updated_hoot = cursor.fetchone()

        connection.commit()
        return jsonify(updated_hoot), 200

    except Exception as error:
        connection.rollback()
        return jsonify({"error": str(error)}), 500
    finally:
        connection.close()


@hoots_blueprint.route("/hoots/<int:hoot_id>", methods=["DELETE"])
@token_required
def delete_hoot(hoot_id):
    connection = get_db_connection()
    try:
        cursor = connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        cursor.execute("SELECT * FROM hoots WHERE id = %s", (hoot_id,))
        hoot_to_delete = cursor.fetchone()
        if hoot_to_delete is None:
            return jsonify({"error": "Hoot not found"}), 404

        # IMPORTANTE: usar !=, no "is not"
        if hoot_to_delete["author"] != g.user["id"]:
            return jsonify({"error": "Unauthorized"}), 401

        cursor.execute("DELETE FROM hoots WHERE id = %s", (hoot_id,))

        connection.commit()
        return jsonify(hoot_to_delete), 200

    except Exception as error:
        connection.rollback()
        return jsonify({"error": str(error)}), 500
    finally:
        connection.close()
