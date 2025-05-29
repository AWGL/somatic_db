// get variable from data-attribute in script tag. Must be before document.ready
const data = document.currentScript.dataset;
const template = data.template;

// load these after the page has loaded
$(document).ready( function() {

    // remove anthing after the hash in the URL, to prevent carrying over from a previous analysis (see issue #47)
    var uri = window.location.toString();
    if (uri.indexOf("#") > 0) {
        var clean_uri = uri.substring(0, uri.indexOf("#"));
        window.history.replaceState({}, document.title, clean_uri);
    }

    // set columns list depending on template, datatables wont render if the length of columns is different
    if (template == 'worksheet') {
        var cols = [
            {orderable: true},
            {orderable: true},
            {orderable: true},
            {orderable: true},
            {orderable: false},
        ]
    } else {
        var cols = [
            {orderable: true},
            {orderable: true},
            {orderable: true},
            {orderable: true},
            {orderable: true},
            {orderable: false},
        ]
    }

    // Inititialise DataTable
    $('#samples-table').DataTable({
        paging: true,
        columns: cols,
        info: true,
        pageLength: 25,
        searching: true,
        aaSorting: [],
        language: {
            searchPlaceholder: "Search by sample ID, panel, status or user",
            search: "",
        },
        initComplete: function () {
            $('.dataTables_filter input[type="search"]').css({ 'width': '500px', 'display': 'inline-block' });
        },
    });
} );

// pull analysis PK into the unnassign modal
$('#unassign-modal').on('show.bs.modal', function (event) {
    // extract variables from button tags
    var button = $(event.relatedTarget);
    var pk = button.data('pk');
    var sample = button.data('sample');
    var panel = button.data('panel');
    var status = button.data('status');
    var assigned = button.data('user');
    var modal = $(this);

    // fill out table of sample details
    modal.find('.modal-sample').text(sample);
    modal.find('.modal-panel').text(panel);
    modal.find('.modal-status').text(status);
    modal.find('.modal-assigned').text(assigned);

    // put sample PK into hidden form so that it can be passed to backend
    document.getElementById ('id_unassign').value = pk;
})

// pull analysis PK into the reopen modal
$('#reopen-modal').on('show.bs.modal', function (event) {
    // extract variables from button tags
    var button = $(event.relatedTarget);
    var pk = button.data('pk');
    var sample = button.data('sample');
    var panel = button.data('panel');
    var assigned = button.data('user');
    var modal = $(this);

    // fill out table of sample details
    modal.find('.modal-sample').text(sample);
    modal.find('.modal-panel').text(panel);
    modal.find('.modal-assigned').text(assigned);

    // put sample PK into hidden form so that it can be passed to backend
    document.getElementById ('id_reopen_analysis').value = pk;
})

// pull analysis PK into the check modal
$('#check-modal').on('show.bs.modal', function (event) {
    // extract variables from button tags
    var button = $(event.relatedTarget);
    var pk = button.data('pk');
    var sample = button.data('sample');
    var panel = button.data('panel');
    var ws = button.data('ws');
    var run = button.data('run');
    var modal = $(this);

    // fill out table of sample details
    modal.find('.modal-pk').text(pk);
    modal.find('.modal-sample').text(sample);
    modal.find('.modal-panel').text(panel);
    modal.find('.modal-ws').text(ws);
    modal.find('.modal-run').text(run);

    // put sample PK into hidden form so that it can be passed to backend
    document.getElementById ('id_sample').value = pk;
})