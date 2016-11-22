$(document).ready(function () {
    /*
    This repeats every 3 seconds to check if the server is back online. Sends the browser to / if it is started.
    This sometimes creates an error in CherryPy because we ask for a response when the server is turned off.
    */

    $.post("/update_now", {
        "mode": "update_now"
    })
    .done(function(r){
        console.log(r);
        if(r == "failed"){
            $("#thinker").fadeOut();
            $("span.msg").text("Update failed. Check logs for more information.");

        }else if(r == "true"){
            // if the update succeeds we"ll start checking for the server to come back online
            var check = setInterval(function(){
                $.post("/server_status", {
                    "mode": "online"
                })
                .done(function(r){
                    console.log(r);
                    if(r == "states.STARTED"){
                        $("span.msg").text("Update successful!");
                        setTimeout(function() {window.location = "/";},3000);
                    }
                })
                .fail(function(r){
                    return;
                });
            }, 3000);

        }else{
            $("#thinker").fadeOut();
            $("span.msg").text("Unknown response. Check logs for more information.");
        }
    });
});