$(window).load(function() {
    $('#current-activity-wrapper').hide();
    $('#next-activities').hide();
    if (activities_index < 1) {
        $('#prev-activities').hide();
    }
    console.log('Loaded window.');
    $('#activity-input').val('');
    get_activities();
    if (underway == 1) {
        var activity = {'description':current_description,
        'start':current_start_time};
        begin_activity(activity);
    }
});

$('#activity-form').submit(function(event) {
    event.preventDefault();
    var button = $('#activity-button');
    var state = button.attr('data-state');
    if (state == 'waiting') {
        console.log('Request in progress.');
        return;
    }
    button.attr('data-state', 'waiting');
    if (button.text() == 'Begin') {
        $.ajax('/start-activity', {
        method: 'POST',
        data: {
            description: $('#activity-input').val(),
            csrf_token: csrf_token,
            user_id: user_id
        },
        success: function(result) {
            console.log('Started activity.');
            begin_activity(result);
        },
        error: function() {
            console.log('Could not start activity.');
            button.attr('data-state', 'ready');
        }
     });
    }
    else if (button.text() == 'Finish') {
        $.ajax('/end-activity', {
        method: 'POST',
        data: {
            csrf_token: csrf_token,
            user_id: user_id
        },
        success: function(result) {
            console.log('Ended activity.');
            finish_activity();
            get_activities();
        },
        error: function() {
            console.log('Could not end activity.');
            button.attr('data-state', 'ready');
        }
     });
    }
});

$('#next-activities').click( function() {
    activities_index += 1;
    var ret = get_activities();
    if (ret == 0) {
        activities_index -= 1;
    }
    else {
        $('#prev-activities').show();
    }
});

$('#prev-activities').click( function() {
   if (activities_index < 1) {
       return;
   }
    activities_index -= 1;
    var ret = get_activities();
    if (ret == 0) {
        activities_index += 1;
        return;
    }
    if (activities_index < 1) {
        $('#prev-activities').hide();
    }
});

function begin_activity(activity) {
    var button = $('#activity-button');
    $('#activity-input').prop('disabled', true);
    $('#activity-input').val('');
    button.text('Finish');
    button.attr('data-state', 'ready');
    $('#current-activity-description').text(activity.description);
    var m = moment.utc(activity.start);
    m.local();
    $('#current-activity-start').text(m.format('h:mma, MMM Do YYYY'));
    $('#current-activity-wrapper').show();
}

function finish_activity() {
    var button = $('#activity-button');
    activities_index = 0;
    $('#activity-input').prop('disabled', false);
    button.text('Begin');
    button.attr('data-state', 'ready');
    $('#prev-activities').hide();
    $('#current-activity-wrapper').hide();
}

var activity_templ = '<li>{{ description }}<ul><li>Started {{ start }}</li><li>Ended {{ end }}</li><li>{{ duration }}</li></ul></li>';

function populate_activities(obj) {
    $('#activity-list li').remove();
    $.each(obj.activities, function(index, value) {
        var activity_obj = {};
        activity_obj.description = value.description;
        var m = moment.utc(value.start_time);
        m.local();
        activity_obj.start = m.format('h:mma, MMM Do YYYY');
        m = moment.utc(value.end_time);
        m.local();
        activity_obj.end = m.format('h:mma, MMM Do YYYY');
        activity_obj.duration = get_duration_string(value.duration);
        var activity_elt = Mustache.render(activity_templ, activity_obj);
        $('#activity-list').append(activity_elt);
    });
}

function get_duration_string(duration) {
    str = '';
    var seconds = 0;
    var minutes = 0;
    var hours = 0;

    if (duration < 60) {
        seconds = Math.floor(duration);
        str = seconds.toString() + ' seconds';
    }
    else if (duration < 3600) {
        minutes = Math.floor(duration/60);
        seconds = Math.floor(duration % 60);
        str = minutes.toString() + ' minutes, ' + seconds.toString() + ' seconds';
    }
    else {
        hours = Math.floor(duration/3600);
        minutes = Math.floor((duration%3600)/60);
        seconds = Math.floor(duration % 60);
        str = hours.toString() + ' hours, ' + minutes.toString() + ' minutes, ' + seconds.toString() + ' seconds';
    }
    return str;
}

function get_activities() {
    $.ajax('/get-activities', {
        method: 'POST',
        data: {
            csrf_token: csrf_token,
            user_id: user_id,
            index: activities_index
        },
        success: function(result) {
            console.log('Received list of activities.');
            populate_activities(result);
            if (result.has_next == 1) {
                $('#next-activities').show();
            }
            else {
                $('#next-activities').hide();
            }
            return 1;
        },
        error: function(result) {
            console.log('Did not receive list of activities.');
            return 0;
        }
    });
}