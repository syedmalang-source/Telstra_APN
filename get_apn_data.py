import json
import csv
import urllib3
import requests
from requests.structures import CaseInsensitiveDict

urllib3.disable_warnings(
    urllib3.exceptions.InsecureRequestWarning
)

requests.packages.urllib3.disable_warnings()


# ============================================================
# CONFIGURATION
# ============================================================

token = "Token XXXX"
vco_url = "https://vco308-syd1.velocloud.net/portal/"

output_file = "cellular_apn_results.csv"


# ============================================================
# API CALL
# ============================================================

def api_call(method, params):

    headers = CaseInsensitiveDict()

    headers["Authorization"] = token
    headers["Content-Type"] = (
        "application/x-www-form-urlencoded"
    )

    data = {
        "id": 0,
        "jsonrpc": "2.0",
        "method": method,
        "params": params
    }

    try:

        response = requests.post(
            vco_url,
            headers=headers,
            data=json.dumps(data),
            verify=False,
            timeout=60
        )

        response.raise_for_status()

        result = response.json()

        if "error" in result:

            return result

        return result

    except Exception as e:

        print(
            f"REQUEST ERROR - {method}: {e}"
        )

        return {}


# ============================================================
# GET ENTERPRISES
# ============================================================

def get_enterprise_ids():

    method = "enterprise/getEnterprisesWithProperty"

    params = {
        "name":
            "vco.enterprise.edgeImageManagement.enable",

        "value":
            "true"
    }

    parsed = api_call(
        method,
        params
    )

    if "error" in parsed:

        print(
            f"API ERROR - {method}: "
            f"{parsed['error']}"
        )

        return []

    result = parsed.get(
        "result",
        []
    )

    if not isinstance(
        result,
        list
    ):

        return []

    enterprises = []

    for item in result:

        if not isinstance(
            item,
            dict
        ):

            continue

        enterprises.append(
            {
                "id":
                    item.get("id"),

                "name":
                    item.get(
                        "name",
                        "Unknown Enterprise"
                    ),

                "logicalId":
                    item.get(
                        "logicalId",
                        ""
                    )
            }
        )

    return enterprises


# ============================================================
# GET EDGES
# ============================================================

def get_edges(
    ent
):

    method = "enterprise/getEnterpriseEdgeList"

    params = {

        "enterpriseId":
            ent["id"],

        "with": [
            "site",
            "ha",
            "configuration",
            "recentLinks",
            "cloudServices",
            "nvsFromEdge",
            "vnfs",
            "certificateSummary",
            "secureDeviceSecrets"
        ],

        "sortBy": [
            {
                "attribute":
                    "edgeState",

                "type":
                    "ASC"
            }
        ],

        "_filterSpec":
            True
    }

    parsed = api_call(
        method,
        params
    )

    if "error" in parsed:

        print(
            f"API ERROR - {method}: "
            f"{parsed['error']}"
        )

        return []

    result = parsed.get(
        "result"
    )

    edges = []

    # --------------------------------------------------------
    # RESULT = LIST
    # --------------------------------------------------------

    if isinstance(
        result,
        list
    ):

        edges = result

    # --------------------------------------------------------
    # RESULT = DICT
    # --------------------------------------------------------

    elif isinstance(
        result,
        dict
    ):

        # First look for direct edge objects.

        for value in result.values():

            if not isinstance(
                value,
                dict
            ):

                continue

            if value.get(
                "id"
            ):

                edges.append(
                    value
                )

        # Try common nested containers.

        if not edges:

            for key in [
                "edges",
                "edgeList",
                "items",
                "data"
            ]:

                value = result.get(
                    key
                )

                if isinstance(
                    value,
                    list
                ):

                    edges = value

                    break

    # --------------------------------------------------------
    # Remove invalid objects
    # --------------------------------------------------------

    valid_edges = []

    for edge in edges:

        if not isinstance(
            edge,
            dict
        ):

            continue

        if not edge.get(
            "id"
        ):

            continue

        valid_edges.append(
            edge
        )

    # --------------------------------------------------------
    # Deduplicate
    # --------------------------------------------------------

    unique = {}

    for edge in valid_edges:

        unique[
            str(edge["id"])
        ] = edge

    return list(
        unique.values()
    )


# ============================================================
# GET EDGE CONFIGURATION STACK
# ============================================================

def get_edge_configstack(
    edge_id,
    ent_id
):

    method = "edge/getEdgeConfigurationStack"

    # ========================================================
    # FIRST TRY - OLD WORKING FORMAT
    # ========================================================

    params = {
        "edgeId":
            edge_id,

        "enterpriseId":
            ent_id,

        "with": [
            "modules"
        ]
    }

    parsed = api_call(
        method,
        params
    )

    # ========================================================
    # IF SUCCESSFUL
    # ========================================================

    if "result" in parsed:

        return parsed

    # ========================================================
    # CHECK ERROR
    # ========================================================

    error = parsed.get(
        "error",
        {}
    )

    error_message = str(
        error.get(
            "message",
            ""
        )
    )

    # ========================================================
    # RETRY WITHOUT "WITH"
    # ========================================================

    if (
        "additionalProperty" in
        error_message
        and
        '"with"' in
        error_message
    ):

        print(
            "    Retrying configuration API "
            "without 'with' parameter..."
        )

        params = {
            "edgeId":
                edge_id,

            "enterpriseId":
                ent_id
        }

        parsed = api_call(
            method,
            params
        )

        return parsed

    # ========================================================
    # OTHER ERROR
    # ========================================================

    return parsed


# ============================================================
# FIND MODULE LIST
# ============================================================

def find_module_lists(
    obj
):

    """
    Find all occurrences of:

        "modules": [...]

    anywhere in the configuration response.
    """

    found = []

    if isinstance(
        obj,
        dict
    ):

        if isinstance(
            obj.get("modules"),
            list
        ):

            found.append(
                obj["modules"]
            )

        for value in obj.values():

            found.extend(
                find_module_lists(value)
            )

    elif isinstance(
        obj,
        list
    ):

        for item in obj:

            found.extend(
                find_module_lists(item)
            )

    return found


# ============================================================
# GET CELLULAR APN
# ============================================================

def get_cellular_apn_setting(
    config
):

    """
    Search for:

        deviceSettings
             |
             +-- data
                  |
                  +-- routedInterfaces
                       |
                       +-- cellular
                            |
                            +-- apn
    """

    module_lists = find_module_lists(
        config
    )

    for modules in module_lists:

        for module in modules:

            if not isinstance(
                module,
                dict
            ):

                continue

            if module.get(
                "name"
            ) != "deviceSettings":

                continue

            try:

                data = module.get(
                    "data"
                )

                if not isinstance(
                    data,
                    dict
                ):

                    continue

                routed_interfaces = data.get(
                    "routedInterfaces",
                    []
                )

                if not isinstance(
                    routed_interfaces,
                    list
                ):

                    continue

                for interface in routed_interfaces:

                    if not isinstance(
                        interface,
                        dict
                    ):

                        continue

                    cellular = interface.get(
                        "cellular"
                    )

                    if not isinstance(
                        cellular,
                        dict
                    ):

                        continue

                    # ----------------------------------------
                    # Cellular interface found
                    # ----------------------------------------

                    apn = cellular.get(
                        "apn"
                    )

                    if apn:

                        return apn

            except Exception:

                continue

    return None


# ============================================================
# PROCESS EDGE
# ============================================================

def process_edge(
    edge,
    enterprise
):

    edge_id = edge.get(
        "id"
    )

    edge_name = edge.get(
        "name",
        f"Edge-{edge_id}"
    )

    # --------------------------------------------------------
    # Site
    # --------------------------------------------------------

    site = edge.get(
        "site",
        {}
    )

    if isinstance(
        site,
        dict
    ):

        site_name = site.get(
            "name",
            "Unknown Site"
        )

    else:

        site_name = "Unknown Site"

    print(
        f"Edge: "
        f"{site_name} / "
        f"{edge_name} "
        f"(ID {edge_id})"
    )

    # ========================================================
    # GET CONFIG
    # ========================================================

    config_response = get_edge_configstack(
        edge_id,
        enterprise["id"]
    )

    if not config_response:

        print(
            "    No configuration - skipping"
        )

        return None

    if "error" in config_response:

        print(
            f"    Configuration error: "
            f"{config_response['error']}"
        )

        return None

    # ========================================================
    # SEARCH APN
    # ========================================================

    apn = get_cellular_apn_setting(
        config_response
    )

    if apn:

        print(
            f"    >>> CELLULAR APN FOUND: "
            f"{apn}"
        )

        return {
            "enterprise_id":
                enterprise["id"],

            "enterprise_name":
                enterprise["name"],

            "site_name":
                site_name,

            "edge_id":
                edge_id,

            "edge_name":
                edge_name,

            "cellular_apn":
                apn
        }

    print(
        "    No cellular APN"
    )

    return None


# ============================================================
# PROCESS ENTERPRISE
# ============================================================

def process_enterprise(
    enterprise
):

    print()
    print(
        "============================================================"
    )

    print(
        f"Processing Enterprise: "
        f"{enterprise['name']} "
        f"({enterprise['id']})"
    )

    print(
        "============================================================"
    )

    edges = get_edges(
        enterprise
    )

    print(
        f"Found {len(edges)} edges"
    )

    results = []

    for edge in edges:

        try:

            result = process_edge(
                edge,
                enterprise
            )

            if result:

                results.append(
                    result
                )

        except Exception as e:

            print(
                f"    ERROR processing edge "
                f"{edge.get('id')}: {e}"
            )

            continue

    return results


# ============================================================
# WRITE CSV
# ============================================================

def write_csv(
    results
):

    fieldnames = [
        "enterprise_id",
        "enterprise_name",
        "site_name",
        "edge_id",
        "edge_name",
        "cellular_apn"
    ]

    with open(
        output_file,
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames
        )

        writer.writeheader()

        writer.writerows(
            results
        )

    print()
    print(
        f"CSV saved: {output_file}"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print(
        "============================================================"
    )

    print(
        "VCO CELLULAR APN AUDIT"
    )

    print(
        "============================================================"
    )

    enterprises = get_enterprise_ids()

    print(
        f"Found {len(enterprises)} enterprises"
    )

    if not enterprises:

        print(
            "No enterprises found."
        )

        return

    all_results = []

    for enterprise_number, enterprise in enumerate(
        enterprises,
        start=1
    ):

        print()
        print(
            f"######## Enterprise "
            f"{enterprise_number}/"
            f"{len(enterprises)} ########"
        )

        try:

            results = process_enterprise(
                enterprise
            )

            all_results.extend(
                results
            )

        except Exception as e:

            print(
                f"Enterprise error: "
                f"{enterprise['name']}: {e}"
            )

            continue

    # ========================================================
    # SUMMARY
    # ========================================================

    print()
    print(
        "============================================================"
    )

    print(
        "AUDIT COMPLETE"
    )

    print(
        "============================================================"
    )

    print(
        f"Enterprises scanned : "
        f"{len(enterprises)}"
    )

    print(
        f"Edges with APN      : "
        f"{len(all_results)}"
    )

    print()

    for result in all_results:

        print(
            f"{result['enterprise_name']} | "
            f"{result['site_name']} | "
            f"{result['edge_name']} | "
            f"{result['cellular_apn']}"
        )

    write_csv(
        all_results
    )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    main()
