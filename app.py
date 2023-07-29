from flask import *
from pymongo.mongo_client import *
from flask_session import *
from pymongo import *
import jwt
from datetime import datetime, timedelta
from jwt import encode
url = "mongodb+srv://naup96321:aaa@naup.xsauomk.mongodb.net/?retryWrites=true&w=majority"
client = MongoClient(url)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'naup'
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

def decode_jwt_token(jwt_token):
    try:
        payload = jwt.decode(jwt_token, app.config['SECRET_KEY'], algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return None  # Token has expired
    except jwt.InvalidTokenError:
        return None  # Invalid token

def check_username_exists(username):
    if client.userdata.user.find_one({"username": username}):
        return True
    else:
        return False

def get_list_data_and_handle():
    current_account = session.get("username") 
    user_orders = list(client.orderdata.users_order.find({"account": current_account}))

    orders = []
    for order in user_orders:
        order_data = {
            "item_id": order["item_id"],
            "account": order["account"],
            "price": order["price"]
        }
        orders.append(order_data)
    return orders

def get_all_list_data():
    
    user_orders = list(client.orderdata.users_order.find())

    orders = []
    for order in user_orders:
        order_data = {
            "item_id": order["item_id"],
            "account": order["account"],
            "price": order["price"]
        }
        orders.append(order_data)
    return orders


@app.route("/")
def home():
    return render_template("home.html")

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/your_orderlist")
def your_orderlist():
    if session.get("logged_in"):
        if session["permissions"]=="USER":
            return render_template("user_order_list.html")    
        elif session["permissions"]=="ADMIN":
            return render_template("admin_order_list.html") 
    return redirect(url_for("status"))


@app.route('/allorders', methods=['GET'])
def get_allorders():
    orders=get_all_list_data()
    return jsonify(orders)


@app.route('/orders', methods=['GET'])
def get_orders():
    orders=get_list_data_and_handle()
    return jsonify(orders)

@app.route('/orders/<int:order_id>', methods=['GET'])
def get_order(order_id):
    order = client.orderdata.users_order.find_one({"item_id": order_id})
    if order:
        order_data = {
            "item_id": order["item_id"],
            "account": order["account"],
            "price": order["price"],
            "Ereshkigal":order["products"]["Ereshkigal"],
            "HoshinoAi": order["products"]["HoshinoAi"],
            "KusanagiNene":order["products"]["KusanagiNene"] 
        }
        return jsonify(order_data)
    else:
        return jsonify({"error": "Order not found"}), 404


@app.route("/menu")
def menu():
    if session.get("logged_in"):
        return render_template("menu.html") 
    return redirect(url_for("status"))

@app.route("/submit_order", methods=["GET", "POST"])
def submit_order():
    max_item_id_document=client.orderdata.users_order.find_one(sort=[("item_id", DESCENDING)])
    max_item_id=max_item_id_document["item_id"]+1 if max_item_id_document else 1
    
    ereshkigal=int(request.values["ereshkigal"])
    HoshinoAi=int(request.values["HoshinoAi"])
    KusanagiNene=int(request.values["KusanagiNene"])
    
    order_list_data={
        "item_id": max_item_id,
        "account": session["username"],
        "products": {
            "Ereshkigal": ereshkigal,
            "HoshinoAi": HoshinoAi,
            "KusanagiNene": KusanagiNene
        },
        "price": ereshkigal*1000+HoshinoAi*1000+KusanagiNene*1000
    }
    client.orderdata.users_order.insert_one(order_list_data)
    return redirect(url_for("status"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.values["username"]
        password = request.values["password"]
        confirmpassword = request.values["confirmpassword"]
        
        if check_username_exists(username):
            return "該帳號已被註冊"
        else:
            if confirmpassword != password:
                return "密碼不一致"
            elif len(password) <= 6:
                return "密碼長度需大於六個字母"
            else:
                client.userdata.user.insert_one({"username": username, "password": password, "permissions": "USER"})

    return render_template("register.html")

@app.route('/orders/<int:order_id>', methods=['DELETE'])
def delete_order(order_id):
    result=client.orderdata.users_order.delete_one({"item_id": order_id})
    if result.deleted_count>0:
        return jsonify({"message": "訂單已成功刪除"})
    else:
        return jsonify({"error": "找不到該訂單"}), 404

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.values["username"]
        password = request.values["password"]

        user_data = client.userdata.user.find_one({"username": username})

        if user_data:
            other_data = {
                "password": user_data.get("password"),
                "permissions": user_data.get("permissions")
            }
            if other_data["password"] == password:

                # Generate JWT token
                token_payload = {
                    "username": username,
                    "permissions": other_data["permissions"],
                    "exp": datetime.utcnow() + timedelta(days=1)  # Token expiration time
                }
                jwt_token = jwt.encode(token_payload, app.config['SECRET_KEY'], algorithm='HS256')

                # Set JWT token in the session cookie
                response = redirect(url_for("status"))
                response.set_cookie("jwt_token", jwt_token, httponly=True)

                return response

            else:
                return "密碼錯誤"

        else:
            return "帳號不存在"

    if session.get("logged_in"):
        return redirect(url_for("status"))

    return render_template("login.html")


@app.route("/status")
def status():
    jwt_token = request.cookies.get("jwt_token")

    if jwt_token:
        decoded_payload = decode_jwt_token(jwt_token)
        if decoded_payload:
            session["logged_in"] = True
            session["permissions"] = decoded_payload["permissions"]
            session["username"] = decoded_payload["username"]
            return render_template("home.html")

    # Clear the session if the JWT token is invalid or missing
    session.clear()
    return redirect(url_for("home"))

    

@app.route("/logout")
def logout():
    response = redirect(url_for("home"))
    response.delete_cookie("jwt_token")  # Clear the JWT token from the session cookie
    session.clear()  # Clear the Flask session
    return response



if __name__ == "__main__":
    app.run(debug=True)
