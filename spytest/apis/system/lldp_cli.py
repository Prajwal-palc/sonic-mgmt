# This file contains additional LLDP CLI validation APIs
# Author: Shiva
# Created: 2026

from spytest import st


def get_lldp_help(dut, cli_type=""):
    """
    Get LLDP help command output
    Author: Shiva

    :param dut: Device Under Test
    :param cli_type: CLI type (klish/click)
    :return: List of dictionaries containing help command output

    Example output for 'show lldp ?':
    [
        {'option': 'neighbor', 'description': 'Display LLDP neighbor information'},
        {'option': 'statistics', 'description': 'Display LLDP statistics information'},
        {'option': 'table', 'description': 'Display LLDP table information'}
    ]
    """
    cli_type = st.get_ui_type(dut, cli_type=cli_type)

    if cli_type == "klish":
        # Execute help command - the '?' triggers help output
        command = "show lldp ?"
        output = st.show(dut, command, type=cli_type, skip_tmpl=True)
        return output
    elif cli_type == "click":
        command = "show lldp --help"
        output = st.show(dut, command, type=cli_type, skip_tmpl=True)
        return output
    else:
        st.log("Unsupported cli type")
        return []
