import streamlit as st
import pandas as pd
import psycopg2
import plotly.express as px
from datetime import date

# ------------------------------
# Database connection
# ------------------------------
def run_query(query, params=None):
    conn = psycopg2.connect(
        host="localhost",
        database="loacl_food",   # ensure DB is created
        user="postgres",
        password="Amrita@1911",
        port="5432"
    )
    df = pd.read_sql(query, conn, params=params)
    conn.close()
    return df

def execute_query(query, params=None):
    conn = psycopg2.connect(
        host="localhost",
        database="loacl_food",
        user="postgres",
        password="Amrita@1911",
        port="5432"
    )
    cur = conn.cursor()
    cur.execute(query, params)
    conn.commit()
    cur.close()
    conn.close()

# ------------------------------
# Streamlit Layout
# ------------------------------
st.set_page_config(page_title="Food Donation Dashboard", layout="wide")
st.title("🍴 Food Donation Management Dashboard")

menu = ["Filter Donations", "Contacts", "CRUD", "Insights"]
choice = st.sidebar.radio("Select Section", menu)

# ------------------------------
# 1. Filter Donations
# ------------------------------
if choice == "Filter Donations":
    st.header("🔍 Filter Food Donations")

    locations = run_query("SELECT DISTINCT location FROM food_listings ORDER BY 1;")["location"].tolist()
    providers = run_query("SELECT DISTINCT name FROM providers ORDER BY 1;")["name"].tolist()
    food_types = run_query("SELECT DISTINCT food_type FROM food_listings ORDER BY 1;")["food_type"].tolist()

    sel_loc = st.multiselect("Filter by Location", locations)
    sel_prov = st.multiselect("Filter by Provider", providers)
    sel_type = st.multiselect("Filter by Food Type", food_types)

    query = """
        SELECT f.food_id, f.food_name, f.food_type, f.meal_type, f.quantity,
               f.location, f.expiry_date, f.is_expired,
               p.name AS provider_name, p.city
        FROM food_listings f
        JOIN providers p ON f.provider_id = p.provider_id
        WHERE (%s = '{}' OR f.location = ANY(%s))
          AND (%s = '{}' OR p.name = ANY(%s))
          AND (%s = '{}' OR f.food_type = ANY(%s))
        ORDER BY f.expiry_date NULLS LAST;
    """
    df = run_query(query, (sel_loc, sel_loc, sel_prov, sel_prov, sel_type, sel_type))
    st.dataframe(df, use_container_width=True)

# ------------------------------
# 2. Contacts
# ------------------------------
elif choice == "Contacts":
    st.header("📞 Contact Providers & Receivers")

    st.subheader("Providers")
    provs = run_query("SELECT provider_id, name, COALESCE(clean_contact, contact) AS contact, city, address FROM providers order by provider_id ASC;")
    st.dataframe(provs, use_container_width=True)

    st.subheader("Receivers")
    recs = run_query("SELECT receiver_id, name, COALESCE(clean_contact, contact) AS contact, city FROM receivers order by receiver_id ASC;")
    st.dataframe(recs, use_container_width=True)

# ------------------------------
# 3. CRUD Operations
# ------------------------------
elif choice == "CRUD":
    st.header("⚙️ CRUD Operations")

    crud_tabs = st.tabs(["Food Listings", "Providers", "Receivers", "Claims"])

    # Food Listings
    with crud_tabs[0]:
        st.subheader("Add New Food Item")
        with st.form("add_food"):
            name = st.text_input("Food Name")
            qty = st.number_input("Quantity", 1, step=1)
            prov_id = st.number_input("Provider ID", 1, step=1)
            loc = st.text_input("Location")
            ftype = st.text_input("Food Type")
            mtype = st.text_input("Meal Type")
            exp = st.date_input("Expiry Date", value=date.today())
            submit = st.form_submit_button("Add")
            if submit:
                execute_query("""
                    INSERT INTO food_listings (food_name, quantity, provider_id, location, food_type, meal_type, expiry_date, is_expired)
                    VALUES (%s,%s,%s,%s,%s,%s,%s, FALSE)
                """, (name, qty, prov_id, loc, ftype, mtype, exp))
                st.success("Food item added!")

        st.divider()
        st.subheader("Update Food Item")
        fid = st.number_input("Food ID to Update", 1, step=1)
        new_qty = st.number_input("New Quantity", 0, step=1)
        if st.button("Update Food Quantity"):
            execute_query("UPDATE food_listings SET quantity=%s WHERE food_id=%s", (new_qty, fid))
            st.success("Updated successfully!")

        st.divider()
        st.subheader("Delete Food Item")
        del_id = st.number_input("Food ID to Delete", 1, step=1, key="del_food")
        if st.button("Delete Food"):
            execute_query("DELETE FROM food_listings WHERE food_id=%s", (del_id,))
            st.success("Food deleted!")

    # Providers
    with crud_tabs[1]:
        st.subheader("Add Provider")
        pname = st.text_input("Provider Name")
        pcity = st.text_input("City")
        paddr = st.text_input("Address")
        pcontact = st.text_input("Contact")
        if st.button("Add Provider"):
            execute_query("INSERT INTO providers (name, city, address, contact) VALUES (%s,%s,%s,%s)", (pname, pcity, paddr, pcontact))
            st.success("Provider added!")

    # Receivers
    with crud_tabs[2]:
        st.subheader("Add Receiver")
        rname = st.text_input("Receiver Name")
        rcity = st.text_input("City", key="rcity")
        raddr = st.text_input("Address", key="raddr")
        rcontact = st.text_input("Contact", key="rcontact")
        if st.button("Add Receiver"):
            execute_query("INSERT INTO receivers (name, city, address, contact) VALUES (%s,%s,%s,%s)", (rname, rcity, raddr, rcontact))
            st.success("Receiver added!")

    # Claims
    with crud_tabs[3]:
        st.subheader("Add Claim")
        food_id = st.number_input("Food ID", 1, step=1)
        rec_id = st.number_input("Receiver ID", 1, step=1)
        prov_id = st.number_input("Provider ID", 1, step=1)
        status = st.selectbox("Status", ["Pending", "Completed", "Cancelled"])
        if st.button("Add Claim"):
            execute_query("INSERT INTO claims (food_id, receiver_id, provider_id, status, timestamp) VALUES (%s,%s,%s,%s,NOW())", (food_id, rec_id, prov_id, status))
            st.success("Claim added!")

# ------------------------------
# 4. Insights (15 queries)
# ------------------------------
elif choice == "Insights":
    st.header("📊 Insights")

    # 1 Providers & Receivers by city
    q1 = """
    SELECT city,
           COUNT(*) FILTER (WHERE role = 'Provider') AS providers_count,
           COUNT(*) FILTER (WHERE role = 'Receiver') AS receivers_count
    FROM (
        SELECT city, 'Provider' AS role FROM providers
        UNION ALL
        SELECT city, 'Receiver' AS role FROM receivers
    ) t
    GROUP BY city
    ORDER BY city;
    """
    st.subheader("1. Providers & Receivers by City")
    st.dataframe(run_query(q1))

    # 2 Provider type with most contributions
    q2 = """
    SELECT type, SUM(quantity) AS total_quantity
    FROM food_listings f
    JOIN providers p ON f.provider_id = p.provider_id
    GROUP BY type
    ORDER BY total_quantity DESC
    LIMIT 1;
    """
    st.subheader("2. Provider Type with Most Contributions")
    st.dataframe(run_query(q2))

    # 3 Provider contacts by city
    cities = run_query("SELECT DISTINCT city FROM providers ORDER BY city;")["city"].tolist()
    selected_city = st.selectbox("Select City", cities)
    q3 = f"SELECT name, type, COALESCE(clean_contact, contact), address FROM providers WHERE city = '{selected_city}';"
    st.subheader(f"3. Provider Contacts in {selected_city}")
    st.dataframe(run_query(q3))

    # 4 Top receivers
    q4 = """
    SELECT r.name AS receiver_name, COUNT(c.claim_id) AS total_claims
    FROM claims c
    JOIN receivers r ON c.receiver_id = r.receiver_id
    GROUP BY r.name
    ORDER BY total_claims DESC
    LIMIT 5;
    """
    st.subheader("4. Top Receivers by Claims")
    st.dataframe(run_query(q4))

    # 5 Total food available
    st.subheader("5. Total Food Quantity Available")
    st.dataframe(run_query("SELECT SUM(quantity) AS total_quantity_available FROM food_listings;"))

    # 6 City with highest listings
    q6 = """
    SELECT location AS city, COUNT(food_id) AS total_listings
    FROM food_listings
    GROUP BY location
    ORDER BY total_listings DESC
    LIMIT 1;
    """
    st.subheader("6. City with Highest Food Listings")
    st.dataframe(run_query(q6))

    # 7 Food type distribution
    q7 = "SELECT food_type, COUNT(food_id) AS total_items FROM food_listings GROUP BY food_type ORDER BY total_items DESC;"
    st.subheader("7. Most Common Food Types")
    fig7 = px.pie(run_query(q7), names="food_type", values="total_items", title="Food Type Distribution")
    st.plotly_chart(fig7)

    # 8 Claims per food item
    q8 = """
    SELECT f.food_name, COUNT(c.claim_id) AS total_claims
    FROM claims c
    JOIN food_listings f ON c.food_id = f.food_id
    GROUP BY f.food_name
    ORDER BY total_claims DESC;
    """
    st.subheader("8. Claims Per Food Item")
    st.dataframe(run_query(q8))

    # 9 Provider with highest successful claims
    q9 = """
    SELECT p.name AS provider_name, COUNT(c.claim_id) AS successful_claims
    FROM claims c
    JOIN food_listings f ON c.food_id = f.food_id
    JOIN providers p ON f.provider_id = p.provider_id
    WHERE c.status = 'Completed'
    GROUP BY p.name
    ORDER BY successful_claims DESC
    LIMIT 1;
    """
    st.subheader("9. Provider with Most Successful Claims")
    st.dataframe(run_query(q9))

    # 10 Claims by status
    q10 = """
    SELECT status, ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM claims), 2) AS percentage
    FROM claims
    GROUP BY status;
    """
    st.subheader("10. Claims by Status (%)")
    fig10 = px.bar(run_query(q10), x="status", y="percentage", text="percentage")
    st.plotly_chart(fig10)

    # 11 Avg claimed food per receiver
    q11 = """
    SELECT r.name AS receiver_name, ROUND(AVG(f.quantity),2) AS avg_claimed_quantity
    FROM claims c
    JOIN receivers r ON c.receiver_id = r.receiver_id
    JOIN food_listings f ON c.food_id = f.food_id
    GROUP BY r.name
    ORDER BY avg_claimed_quantity DESC;
    """
    st.subheader("11. Average Claimed Food Per Receiver")
    st.dataframe(run_query(q11))

    # 12 Most claimed meal type
    q12 = """
    SELECT f.meal_type, COUNT(c.claim_id) AS total_claims
    FROM claims c
    JOIN food_listings f ON c.food_id = f.food_id
    GROUP BY f.meal_type
    ORDER BY total_claims DESC
    LIMIT 1;
    """
    st.subheader("12. Most Claimed Meal Type")
    st.dataframe(run_query(q12))

    # 13 Donations per provider
    q13 = """
    SELECT p.name AS provider_name, SUM(f.quantity) AS total_donated
    FROM food_listings f
    JOIN providers p ON f.provider_id = p.provider_id
    GROUP BY p.name
    ORDER BY total_donated DESC;
    """
    st.subheader("13. Total Donations Per Provider")
    st.dataframe(run_query(q13))

    # 14 Monthly trend
    q14 = """
    SELECT DATE_TRUNC('month', timestamp) AS month, COUNT(*) AS total_claims
    FROM claims
    GROUP BY month
    ORDER BY month;
    """
    st.subheader("14. Monthly Claims Trend")
    fig14 = px.line(run_query(q14), x="month", y="total_claims")
    st.plotly_chart(fig14)

    # 15 Full claims report
    q15 = """
    SELECT c.claim_id, f.food_name, f.meal_type, c.status, c.timestamp,
           p.name AS provider_name, r.name AS receiver_name
    FROM claims c
    JOIN food_listings f ON c.food_id = f.food_id
    JOIN providers p ON f.provider_id = p.provider_id
    JOIN receivers r ON c.receiver_id = r.receiver_id
    ORDER BY c.claim_id;
    """
    st.subheader("15. Full Claims Report")
    st.dataframe(run_query(q15))
