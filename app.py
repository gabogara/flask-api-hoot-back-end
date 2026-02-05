from flask import Flask, jsonify, request, g
from dotenv import load_dotenv
import jwt
import bcrypt
from auth_middleware import token_required
# Add to stack of imports
from auth_blueprint import authentication_blueprint

# Add to list of imports
from hoots_blueprint import hoots_blueprint



load_dotenv()

app = Flask(__name__)
app.register_blueprint(authentication_blueprint)
app.register_blueprint(hoots_blueprint)


# Index route:
@app.route('/')
def index():
  return "Hello, world!"

@app.route('/users')
@token_required
def users_index():
    connection = get_db_connection()
    cursor = connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cursor.execute("SELECT id, username FROM users;")
    users = cursor.fetchall()
    connection.close()
    return jsonify(users), 200

@app.route('/users/<user_id>')
@token_required
def users_show(user_id):
    # If the user is looking for the details of another user, block the request
    # Send a 403 status code to indicate that the user is unauthorized
    if int(user_id) !=g.user["id"]:
        return jsonify({"err": "Unauthorized"}), 403
    connection = get_db_connection()
    cursor = connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cursor.execute("SELECT id, username FROM users WHERE id = %s;", (user_id))
    user = cursor.fetchone()
    connection.close()
    if user is None:
        return jsonify({"err": "User not found"}), 404
    return jsonify(user), 200

# Run our application, by default on port 5000
app.run(debug=True, port=5001)