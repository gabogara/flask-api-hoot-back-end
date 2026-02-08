from flask import Blueprint, jsonify, request, g
import psycopg2.extras

from db_helpers import get_db_connection
from auth_middleware import token_required

comments_blueprint = Blueprint("comments_blueprint", __name__)


@comments_blueprint.route("/hoots/<int:hoot_id>/comments", methods=["POST"])
@token_required
def create_comment(hoot_id):
    connection = get_db_connection()
    try:
        new_comment_data = request.get_json()
        author_id = g.user["id"]

        cursor = connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        cursor.execute(
            """
            INSERT INTO comments (hoot, author, text)
            VALUES (%s, %s, %s)
            RETURNING id
            """,
            (hoot_id, author_id, new_comment_data["text"]),
        )
        comment_id = cursor.fetchone()["id"]

        cursor.execute(
            """
            SELECT c.id,
                   c.author AS comment_author_id,
                   c.text AS comment_text,
                   c.created_at AS "commentCreatedAt",
                   u_comment.username AS comment_author_username
            FROM comments c
            JOIN users u_comment ON c.author = u_comment.id
            WHERE c.id = %s
            """,
            (comment_id,),
        )
        created_comment = cursor.fetchone()

        connection.commit()
        return jsonify(created_comment), 201

    except Exception as error:
        connection.rollback()
        return jsonify({"error": str(error)}), 500
    finally:
        connection.close()


@comments_blueprint.route("/hoots/<int:hoot_id>/comments/<int:comment_id>", methods=["PUT"])
@token_required
def update_comment(hoot_id, comment_id):
    connection = get_db_connection()
    try:
        updated_comment_data = request.get_json()
        cursor = connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # Validar que el comment exista Y pertenezca a ese hoot_id
        cursor.execute(
            "SELECT * FROM comments WHERE id = %s AND hoot = %s",
            (comment_id, hoot_id),
        )
        comment_to_update = cursor.fetchone()
        if comment_to_update is None:
            return jsonify({"error": "Comment not found"}), 404

        # Validar ownership
        if comment_to_update["author"] != g.user["id"]:
            return jsonify({"error": "Unauthorized"}), 401

        cursor.execute(
            """
            UPDATE comments
            SET text = %s
            WHERE id = %s AND hoot = %s
            RETURNING *
            """,
            (updated_comment_data["text"], comment_id, hoot_id),
        )
        updated_comment = cursor.fetchone()

        connection.commit()
        return jsonify({"comment": updated_comment}), 200

    except Exception as error:
        connection.rollback()
        return jsonify({"error": str(error)}), 500
    finally:
        connection.close()


@comments_blueprint.route("/hoots/<int:hoot_id>/comments/<int:comment_id>", methods=["DELETE"])
@token_required
def delete_comment(hoot_id, comment_id):
    connection = get_db_connection()
    try:
        cursor = connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # Validar que el comment exista Y pertenezca a ese hoot_id
        cursor.execute(
            "SELECT * FROM comments WHERE id = %s AND hoot = %s",
            (comment_id, hoot_id),
        )
        comment_to_delete = cursor.fetchone()
        if comment_to_delete is None:
            return jsonify({"error": "Comment not found"}), 404

        # Validar ownership
        if comment_to_delete["author"] != g.user["id"]:
            return jsonify({"error": "Unauthorized"}), 401

        cursor.execute(
            "DELETE FROM comments WHERE id = %s AND hoot = %s",
            (comment_id, hoot_id),
        )

        connection.commit()
        return jsonify({"message": "Comment deleted successfully"}), 200

    except Exception as error:
        connection.rollback()
        return jsonify({"error": str(error)}), 500
    finally:
        connection.close()
