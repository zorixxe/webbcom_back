import os
import psycopg
from psycopg.rows import dict_row
from flask import Flask, request, jsonify, escape
from flask_cors import CORS
from dotenv import load_dotenv

app = Flask(__name__)
CORS(app)
app.config['JSON_AS_ASCII'] = False

load_dotenv()
db_url = os.environ.get("DB_URL")

# dict_row: få query-resultat som list of dicts
conn = psycopg.connect(db_url, row_factory=dict_row, autocommit=True)


@app.route("/")
def index():
    return {"message": "Use /todo for API endpoint"}


def check_key(api_key):
    with conn.cursor() as cur:
        cur.execute("""
            SELECT id
            FROM users
            WHERE api_key = %s""",
                    [api_key])
        return cur.fetchone()['id']


@app.route("/users")
def user():
    try:
        user_id = check_key(request.args.get('api_key'))
    except:
        return {"message": "ERROR: Invalid API-key"}, 401

    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT * 
                FROM users
                WHERE id = %s""", [user_id])
            result = cur.fetchone()
        return result or {"message": "ERROR: no such guest"}, 400
    except:
        # vi kan skriva statuskoden direkt efter response bodyn
        return {"message": "ERROR: something went wrong"}, 400


@app.route("/todo", methods=["GET", "POST"])
def get_todos():

    try:
        user_id = check_key(request.args.get('api_key'))
    except:
        return {"message": "ERROR: Invalid API-key"}, 401

    if request.method == 'GET':
        with conn.cursor() as cur:
            cur.execute(
                """ SELECT todo.id,
                todo.user_id,
                todo.title,
                todo.done,
                todo.due_date,
                todo.created_at,
                todo.updated_at,
                todo.sort_order,
                categories.category_name 
                FROM todo
                INNER JOIN categories 
                ON todo.category_id=categories.id
                WHERE todo.user_id = %s
                ORDER BY due_date ASC""", [
                    user_id
                ])
            result = cur.fetchall()
        return jsonify(result)

    if request.method == 'POST':
        try:
            req_body = request.get_json()
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO todo (
                        user_id,
                        category_id,
                        title,
                        due_date
                    ) VALUES (
                        %s, %s, %s, %s
                    ) RETURNING id
                """, [
                    user_id,
                    req_body['category_id'],
                    escape(req_body['title']),
                    req_body['due_date'],
                ])
                return {"id": cur.fetchone()['id']}
        except Exception as e:
            print(e)
            return {"ERROR": "Check logs for details"}, 400

    else:
        return {"Du använde metoden": request.method}


@app.route("/todo/<int:id>", methods=["PUT", "PATCH", "DELETE"])
def update_todo(id):
    try:
        user_id = check_key(request.args.get('api_key'))
    except:
        return {"message": "ERROR: Invalid API-key"}, 401
    if request.method == "PUT" or request.method == "PATCH":
        try:
            req_body = request.get_json()
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE todo 
                    SET category_id=%s,
                        title=%s,
                        due_date=%s
                    WHERE id=%s AND user_id=%s
                """, [
                    req_body['category_id'],
                    escape(req_body['title']),
                    req_body['due_date'],
                    id,
                    user_id
                ])
                return {"updated todo id": id}

        except Exception as e:
            print(repr(e))
            return {"ERROR": "check logs for details"}, 400

    if request.method == "DELETE":
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    DELETE FROM todo WHERE id=%s AND user_id=%s
                """, [
                    id,
                    user_id
                ])
                return {"deleted id": id}

        except Exception as e:
            print(repr(e))
            return {"ERROR": "check logs for details"}, 400

    else:
        return {"Du använde metoden": request.method}


# Kom ihåg:
# - pip install -r requirements.txt
# - Kopiera/byt namn på .env-example ==> .env och sätt in en riktig DB_URL
# - Ändra portnummer nedan
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8448, debug=True)
