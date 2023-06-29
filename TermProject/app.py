import psycopg2
from flask import Flask, render_template, request

app = Flask(__name__)
connect = psycopg2.connect("dbname=pjdb user=postgres password=1017")
cur = connect.cursor() 
isAdmin = False
userRole = 'tutee'
userID = ''

def get_popular_lst(cur):

    result = []

    cur.execute("with code_num (code, count) as (select code, count(code) from enrollment group by code) select subject_name from code_num, subject where subject.code = code_num.code and count >= all (select count from code_num) limit 1;")
    result.append(cur.fetchall()[0][0])

    cur.execute("with lecture_num (lecture_name, count) as (select lecture_name, count(lecture_name) from enrollment group by lecture_name) select lecture_name from lecture_num where count >= all (select count from lecture_num) limit 1;")
    result.append(cur.fetchall()[0][0])
                
    cur.execute("with tutor_num (tutor, count) as (select tutor, count(tutor) from enrollment group by tutor) select tutor from tutor_num where count >= all (select count from tutor_num) limit 1;")
    result.append(cur.fetchall()[0][0])

    return result

def get_account_info(cur, target_id):

    cur.execute("select * from account;")
    result = cur.fetchall()

    for user in result:
        if user[0] == target_id:
            credit = user[1]
            rating = user[2]
            role = user[3]
            
            return credit, rating, role
    
    return None

def get_score(cur, lec_info):

    code, name, price, tutor = lec_info
    cur.execute("select avg(score) from review where tutor = '{}' and code = '{}' and lecture_name = '{}' and lecture_price = '{}'".format(tutor, code, name, price))

    score = cur.fetchall()[0][0]
    if score == None: score = 0
    
    return round(score, 2)

def get_lectures(cur):

    cur.execute("select * from lecture;")
    result = cur.fetchall()
    ret = []

    for lec in result:
        score = get_score(cur, lec)
        lec = lec + (score, )
        ret.append(lec)

    return ret

#to define similarity of lecture name (reference : https://www.geeksforgeeks.org/python-similarity-metrics-of-strings/)
def levenshtein_distance(s, t):
    m, n = len(s), len(t)
    if m < n:
        s, t = t, s
        m, n = n, m
    d = [list(range(n + 1))] + [[i] + [0] * n for i in range(1, m + 1)]
    for j in range(1, n + 1):
        for i in range(1, m + 1):
            if s[i - 1] == t[j - 1]:
                d[i][j] = d[i - 1][j - 1]
            else:
                d[i][j] = min(d[i - 1][j], d[i][j - 1], d[i - 1][j - 1]) + 1
    return d[m][n]
 
def compute_similarity(input_string, reference_string):
    distance = levenshtein_distance(input_string, reference_string)
    max_length = max(len(input_string), len(reference_string))
    if max_length == 0: return 0
    similarity = 1 - (distance / max_length)
    return similarity
######################################################################################################################

@app.route('/')
def main():
    return render_template("main.html")

@app.route('/login', methods = ['post'])
def login():

    global isAdmin, userRole, userID

    user_id = request.form["id"]
    userID = user_id
    password = request.form["password"]
    send = request.form["send"]

    if send == 'login':
        cur.execute("SELECT * FROM users;")
        result = cur.fetchall()

        for user in result:
            if user_id == user[0] and password == user[1]:
                
                if user_id == 'admin': isAdmin = True
                else: isAdmin = False

                result = get_popular_lst(cur)
                credit, rating, role = get_account_info(cur, user_id)

                if role == 'tutor': userRole = role
                else: userRole = 'tutee'

                lectures = get_lectures(cur)
                # print(lectures)

                return render_template("pay.html", id = user_id, credit = credit, rating = rating, popular = result, lectures = lectures)
            
        return render_template("login_fail.html")

    else:
        return render_template("signup.html")
    
@app.route('/signup', methods = ['post'])
def signup():

    user_id = request.form["id"]
    password = request.form["password"]
    role = request.form["role"]

    cur.execute("SELECT * FROM users;")
    result = cur.fetchall()

    for user in result:
        if user_id == user[0]: return render_template("ID_collision.html")
        
    cur.execute("INSERT INTO users VALUES('{}', '{}');".format(user_id, password))
    cur.execute("INSERT INTO account VALUES('{}', '{}', '{}', '{}');".format(user_id, 10000, 'welcome', role))
    connect.commit()
        
    return render_template("signup_success.html")

@app.route('/admin', methods = ['post'])
def admin():

    if not isAdmin:
        return render_template("admin_only.html")

    else:
        send = request.form["send"]
        if send == "users info": 
            cur.execute("select * from account")
            result = cur.fetchall()

            return render_template("print_users.html", users=result)
        else:
            cur.execute("select * from enrollment")
            result = cur.fetchall()

            return render_template("print_trades.html", trades=result)
        
@app.route('/logout', methods = ['post'])
def logout():

    global isAdmin, userRole, userID
    
    isAdmin = False
    userRole = 'tutee'
    userID = ''

    return render_template('main.html')

@app.route('/mylectures', methods = ['post'])
def mylectures():

    if userRole == 'tutor':

        cur.execute("select subject_name, lecture_name, tutee, lecture_price from enrollment, subject where enrollment.code = subject.code and tutor = '{}';".format(userID))
        my_lecture = cur.fetchall()

        cur.execute("select subject_name, lecture_name, tutor, lecture_price from enrollment, subject where enrollment.code = subject.code and tutee = '{}';".format(userID))
        regi_lecture = cur.fetchall()

        cur.execute("select requester, lecture_name from request where tutor = '{}'".format(userID))
        reqs = cur.fetchall()

        return render_template('tutor_myinfo.html', my_lecture = my_lecture, regi_lecture = regi_lecture, reqs = reqs)
    
    else:
        cur.execute("select subject_name, lecture_name, tutor, lecture_price from enrollment, subject where enrollment.code = subject.code and tutee = '{}';".format(userID))
        regi_lecture = cur.fetchall()

        return render_template('tutee_myinfo.html', regi_lecture = regi_lecture)
    
@app.route('/add', methods = ['post'])
def add():

    if userRole == 'tutee':
        return render_template("invalid.html")
    
    else:
        cur.execute("select * from subject;")
        subjects = cur.fetchall()

        return render_template("add_lecture.html", subjects = subjects)
    
@app.route('/add_lecture', methods = ['post'])
def add_lecture():

    lec_code = request.form["code"]
    lec_name = request.form["name"]
    lec_price = int(request.form["price"])
    lec_tutor = userID

    cur.execute("select * from subject;")
    subjects = cur.fetchall()
    
    flag = False
    for subject in subjects:
        if subject[0] == lec_code: 
            flag = True
            break

    if not flag or lec_price < 0 : return render_template("lecture_add_fail.html")

    cur.execute("SELECT * FROM lecture;")
    lectures = cur.fetchall()

    for lecture in lectures:
        if lec_code == lecture[0] and lec_name == lecture[1] and lec_price == lecture[2] and lec_tutor == lecture[3]:
            return render_template("lecture_add_fail.html")
    
    cur.execute("INSERT INTO lecture VALUES('{}', '{}', '{}', '{}');".format(lec_code, lec_name, lec_price, lec_tutor))
    connect.commit()

    return render_template("lecture_add_success.html")

@app.route('/register', methods = ['post'])
def register():

    code, name, price, tutor = request.form["code"], request.form["name"], int(request.form["price"]), request.form["tutor"]
    lecture_info = (code, name, price, tutor)
    credit, rating, _ = get_account_info(cur, userID)

    # print(code, name, price, tutor, credit, rating, userID)

    # 1. tutor can't register to his/her lecture 
    if tutor == userID: return render_template("lecture_reg_fail.html")

    # calculate discount and final price
    cur.execute("select discount from rating_info where rating = '{}';".format(rating))
    discount_percent = float((cur.fetchall())[0][0])
    # print(discount_percent)

    discount = int(price * discount_percent / 100)
    final_price = price - discount

   # print(discount, final_price)

    # 2. don't have enough credit to register
    if credit < final_price: return render_template("lecture_reg_fail.html")

    # 3. check user already enrolled to same lecture
    cur.execute("select * from enrollment where tutee = '{}';".format(userID))
    user_lec_lst = cur.fetchall()

    for lec in user_lec_lst:
        if tutor == lec[1] and code == lec[2] and name == lec[3] and price == lec[4]:
            return render_template("lecture_reg_fail.html")
        
    return render_template("register.html", lecture = lecture_info, credit = credit, rating = rating, discount = discount, final_price = final_price)

@app.route('/confirm', methods = ['post'])
def confirm():

    code, name, price, tutor = request.form["code"], request.form["name"], int(request.form["price"]), request.form["tutor"]
    credit, final_price = int(request.form["credit"]), int(request.form["final_price"])
    tutee = userID

    #update credit of tutor/tutee
    cur.execute("select * from account;")
    result = cur.fetchall()

    tutor_credit = 0
    for user in result:
        if user[0] == tutor: tutor_credit = int(user[1])

    tutee_credit = credit - final_price
    tutor_credit += price

    cur.execute("update account set credit = {} where id = '{}';".format(tutor_credit, tutor))
    cur.execute("update account set credit = {} where id = '{}';".format(tutee_credit, tutee))
    connect.commit()

    #update rating of tutor/tutee
    cur.execute("select rating, condition from rating_info;")
    result = cur.fetchall()

    condition = {}
    for info in result:
        condition[info[0]] = int(info[1])

    
    base_rating = list(condition.keys())[-1]
    tutee_rating, tutor_rating = base_rating, base_rating

    for r in condition.keys():
        if tutee_credit > condition[r]: 
            tutee_rating = r
            break

    for r in condition.keys():
        if tutor_credit > condition[r]: 
            tutor_rating = r
            break
    
    cur.execute("update account set rating = '{}' where id = '{}';".format(tutor_rating, tutor))
    cur.execute("update account set rating = '{}' where id = '{}';".format(tutee_rating, tutee))
    connect.commit()

    # update enrollment

    cur.execute("INSERT INTO enrollment VALUES('{}', '{}', '{}', '{}', {}, 'false');".format(tutee, tutor, code, name, price))
    connect.commit()
    
    return render_template("lecture_reg_success.html")

@app.route('/review', methods = ['post'])
def review():
    subject, name, price, tutor = request.form["subject"], request.form["name"], int(request.form["price"]), request.form["tutor"]
    cur.execute("select code from subject where subject_name = '{}';".format(subject))
    code = (cur.fetchall())[0][0]
    tutee = userID

    lecture_info = (code, name, price, tutor)

    cur.execute("select is_reviewed from enrollment where tutee = '{}' and tutor = '{}' and code = '{}' and lecture_name = '{}' and lecture_price = '{}';".format(tutee, tutor, code, name, price))
    is_reviewed = (cur.fetchall())[0][0]

    if is_reviewed == 'true': return render_template("review_fail.html")
    else: return render_template("review.html", lecture = lecture_info)

@app.route('/review_confirm', methods = ['post'])
def review_confirm():

    score = float(request.form["score"])
    code, name, price, tutor = request.form["code"], request.form["name"], int(request.form["price"]), request.form["tutor"]
    tutee = userID

    cur.execute("INSERT INTO review VALUES('{}', '{}', '{}', '{}', {}, {});".format(tutee, tutor, code, name, price, score))
    cur.execute("update enrollment set is_reviewed = 'true' where tutee = '{}' and tutor = '{}' and code = '{}' and lecture_name = '{}' and lecture_price = '{}';".format(tutee, tutor, code, name, price))

    connect.commit()

    return render_template("review_success.html")

@app.route('/request_lec', methods = ['post'])
def request_lec():
    lectures = get_lectures(cur)
    return render_template("request.html", lectures = lectures)

@app.route('/request_submit', methods = ['post'])
def request_submit():

    requester = userID
    req_tutor = request.form["tutor"]
    req_lec_name = request.form["lec_name"]

    if req_tutor == requester: return render_template("request_fail.html")

    cur.execute("select id from account where role = 'tutor';")
    tutors = cur.fetchall()

    flag = False
    for tutor in tutors:
        if tutor[0] == req_tutor: 
            flag = True
            break

    if not flag: return render_template("request_fail.html")

    cur.execute("select * from lecture;")
    lectures = cur.fetchall()

    similar_lecs = []

    for lec in lectures:
        lec_name = lec[1]
        lec_sim_score = compute_similarity(lec_name, req_lec_name)
        if lec_sim_score > 0.6: similar_lecs.append(lec)

    return render_template("request_recom.html", lectures = similar_lecs, req_tutor = req_tutor, req_lec_name = req_lec_name)

@app.route('/request_final', methods = ['post'])
def request_final():

    requester = userID
    req_tutor = request.form["tutor"]
    req_lec_name = request.form["lec_name"]

    cur.execute("select * from request;")
    result = cur.fetchall()

    for req in result:
        if requester == req[0] and req_tutor == req[1] and req_lec_name == req[2]:
            return render_template("request_collision.html")

    cur.execute("INSERT INTO request VALUES('{}', '{}', '{}');".format(requester, req_tutor, req_lec_name))
    connect.commit()

    return render_template("request_success.html")

@app.route('/return', methods = ['post', 'get'])
def return_page():

    send = request.form["send"]
    if send == "return":
        return render_template("main.html")
    elif send == "return to pay page" or send == "cancel":
        result = get_popular_lst(cur)
        credit, rating, _ = get_account_info(cur, userID)
        lectures = get_lectures(cur)
        # print(lectures)
        return render_template("pay.html", id = userID, credit = credit, rating = rating, popular = result, lectures = lectures)
 
if __name__ == '__main__':
    app.run()
