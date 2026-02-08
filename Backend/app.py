from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import sqlite3
from datetime import datetime
import os

# Configure Flask to find templates in Frontend folder
app = Flask(
    __name__,
    template_folder=os.path.join(os.path.dirname(__file__), "Frontend"),
    static_folder=os.path.join(os.path.dirname(__file__), "Frontend"),
)
CORS(app)

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "medicine_expiry.db")


def get_db():
    return sqlite3.connect(DB_PATH)


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/add", methods=["POST"])
def add_medicine():
    try:
        data = request.json

        if not data:
            return jsonify({"error": "No data provided"}), 400

        required_fields = ["name", "batch", "expiry", "barcode", "quantity"]
        missing_fields = [field for field in required_fields if field not in data]

        if missing_fields:
            return jsonify(
                {"error": f"Missing fields: {', '.join(missing_fields)}"}
            ), 400

        try:
            quantity = int(data["quantity"])
            if quantity < 0:
                return jsonify({"error": "Quantity must be positive"}), 400
        except ValueError:
            return jsonify({"error": "Quantity must be a number"}), 400

        try:
            datetime.strptime(data["expiry"], "%Y-%m-%d")
        except ValueError:
            return jsonify({"error": "Expiry date must be in YYYY-MM-DD format"}), 400

        conn = get_db()
        cur = conn.cursor()

        cur.execute(
            """
            INSERT INTO medicines (name, batch, expiry, barcode, quantity)
            VALUES (?, ?, ?, ?, ?)
        """,
            (data["name"], data["batch"], data["expiry"], data["barcode"], quantity),
        )

        conn.commit()
        conn.close()
        return jsonify({"message": "Medicine added successfully"}), 201

    except Exception as e:
        return jsonify({"error": f"Failed to add medicine: {str(e)}"}), 500


@app.route("/medicines", methods=["GET"])
def get_medicines():
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT * FROM medicines")
        rows = cur.fetchall()
        conn.close()

        medicines = []
        for r in rows:
            try:
                expiry = datetime.strptime(r[3], "%Y-%m-%d")
                days_left = (expiry - datetime.today()).days

                if days_left < 0:
                    status = "expired"
                elif days_left <= 30:
                    status = "warning"
                else:
                    status = "safe"

                medicines.append(
                    {
                        "id": r[0],
                        "name": r[1],
                        "batch": r[2],
                        "expiry": r[3],
                        "barcode": r[4],
                        "quantity": r[5],
                        "days_left": days_left,
                        "status": status,
                    }
                )
            except ValueError:
                # Skip medicines with invalid date format
                continue

        return jsonify(medicines), 200

    except Exception as e:
        return jsonify({"error": f"Failed to fetch medicines: {str(e)}"}), 500


@app.route("/delete/<int:id>", methods=["DELETE"])
def delete_medicine(id):
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("DELETE FROM medicines WHERE id=?", (id,))

        if cur.rowcount == 0:
            conn.close()
            return jsonify({"error": f"Medicine with id {id} not found"}), 404

        conn.commit()
        conn.close()
        return jsonify({"message": f"Medicine {id} deleted successfully"}), 200

    except Exception as e:
        return jsonify({"error": f"Failed to delete medicine: {str(e)}"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=1000, debug=False)
