import os, json, requests
from github import Github

REPO_FULL = "halitipek/ai-crew-sandbox"
GQL_URL    = "https://api.github.com/graphql"
TOKEN      = os.environ["GH_PAT"]
HEADERS    = {"Authorization": f"Bearer {TOKEN}"}

gh = Github(TOKEN)
repo = gh.get_repo(REPO_FULL)

# ------------------------------------------------------------
def gql(query: str, variables: dict = None):
    resp = requests.post(GQL_URL,
                         headers=HEADERS,
                         json={"query": query, "variables": variables or {}})
    resp.raise_for_status()
    return resp.json()

def fetch_ids():
    # 1) Proje ID'si (SimplyECS Kanban)
    q_proj = """
      query { viewer { projectsV2(first:20) { nodes { id title } } } }
    """
    nodes = gql(q_proj)["data"]["viewer"]["projectsV2"]["nodes"]
    proj = next(n for n in nodes if n["title"] == "SimplyECS Kanban")
    project_id = proj["id"]

    # 2) Status alanı ID'si
    q_field = """
      query($p:ID!){ node(id:$p){
        ... on ProjectV2 { field(name:"Status"){ id } } } }
    """
    field_id = gql(q_field, {"p": project_id})["data"]["node"]["field"]["id"]

    # 3) 'Dev' seçeneği ID'si
    q_opts = """
      query($f:ID!){ node(id:$f){
        ... on ProjectV2SingleSelectField { options { id name } } } }
    """
    opts = gql(q_opts, {"f": field_id})["data"]["node"]["options"]
    dev_option = next(o for o in opts if o["name"] == "Dev")["id"]

    return project_id, field_id, dev_option

PROJECT_ID, STATUS_FIELD_ID, DEV_OPTION_ID = fetch_ids()
# ------------------------------------------------------------

def move_to_dev(item_id: str):
    mutation = """
      mutation($proj:ID!,$item:ID!,$field:ID!,$opt:ID!){
        updateProjectV2ItemFieldValue(input:{
          projectId:$proj itemId:$item fieldId:$field
          value:{ singleSelectOptionId:$opt }})
        { item { id } } }
    """
    gql(mutation, {
        "proj": PROJECT_ID,
        "item": item_id,
        "field": STATUS_FIELD_ID,
        "opt": DEV_OPTION_ID
    })

# --- PR, issue ve item_id oluşturulduktan hemen sonra çağır ---
# item_id = issue.node_id
# move_to_dev(item_id)
# print("Moved card to Dev ✅")
