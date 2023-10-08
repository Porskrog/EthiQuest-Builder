<script type="text/javascript"> 
jQuery(document).ready(function($) {

    // Function to generate a unique ID
    function generateUniqueID() {
        return 'xxxx-xxxx-4xxx-yxxx-xxxx'.replace(/[xy]/g, function(c) {
            const r = (Math.random() * 16) | 0,
                v = c === 'x' ? r : (r & 0x3) | 0x8;
            return v.toString(16);
        });
    }

function getCookie(cname) {
    let name = cname + "=";
    let decodedCookie = decodeURIComponent(document.cookie);
    let ca = decodedCookie.split(';');
    for(let i = 0; i < ca.length; i++) {
        let c = ca[i];
        while (c.charAt(0) === ' ') {
            c = c.substring(1);
        }
        if (c.indexOf(name) === 0) {
            return c.substring(name.length, c.length);
        }
    }
    return "";
}

function setCookie(cname, cvalue, exdays) {
    const d = new Date();
    d.setTime(d.getTime() + (exdays * 24 * 60 * 60 * 1000));
    let expires = "expires="+d.toUTCString();
    document.cookie = cname + "=" + cvalue + ";" + expires + ";path=/";
}

    // Check if the user cookie exists; if not, create one
    let userCookie = getCookie("userCookie");
    if (userCookie === "") {
        userCookie = generateUniqueID();
        setCookie("userCookie", userCookie, 365);
    }

    // Replace this with your deployed API URL
    const API_URL = 'https://ethiquest-builder.onrender.com';

function fetchUnviewedDilemmas(userCookie, callback) {
    $.ajax({
        type: 'GET',
        url: `${API_URL}/get_unviewed_dilemmas`, // Replace with your actual backend URL
        data: {
            user_cookie: userCookie
        },
        success: function(response) {
            callback(null, response.dilemmas);
        },
        error: function(error) {
            console.error("Error fetching unviewed dilemmas:", error);
            callback(error);
        }
    });
}


function fetchRandomDilemma() {
    let userCookie = getCookie("userCookie");
    fetchUnviewedDilemmas(userCookie, function(error, dilemmas) {
        if (error) {
            console.error("Error fetching unviewed dilemmas:", error);
            return;
        }

        if (dilemmas.length === 0) {
            $('#randomDilemmaDisplay').html('<h3>No more dilemmas to display.</h3>');
            return;
        }

        const dilemma = dilemmas[Math.floor(Math.random() * dilemmas.length)];
        let dilemmaHtml = `<h3>${dilemma.question}</h3><ul>`;
        dilemma.options.forEach(function(option) {
            dilemmaHtml += `<li class="option-item" data-id="${option.id}">${option.text}</li>`;
        });
        dilemmaHtml += '</ul>';
        $('#randomDilemmaDisplay').html(dilemmaHtml);
        
        // Clear the option details
        $('#optionDetailsDisplay').html('');

        // Mark this dilemma as viewed
        markDilemmaAsViewed(dilemma.id, userCookie);
    });
}


// Function to mark a dilemma as viewed
function markDilemmaAsViewed(dilemmaId, userCookie) {
    $.ajax({
        type: 'POST',
        url: `${API_URL}/view_dilemma/${dilemmaId}`,
        data: JSON.stringify({
            user_id: userCookie
        }),
        contentType: "application/json; charset=utf-8",
        success: function(response) {
            console.log("Dilemma marked as viewed:", response);
        },
        error: function(error) {
            console.error("Error marking dilemma as viewed:", error);
        }
    });
}

    // Fetch option details
    function fetchOptionDetails(OptionID) {
        $.ajax({
            type: 'GET',
            url: `${API_URL}/get_option_details/${OptionID}`,
            success: function(response) {
                const option = response.option;
                let optionDetailsHtml = `<h4>${option.text}</h4><p>Pros: ${option.pros}</p><p>Cons: ${option.cons}</p>`;
                $('#optionDetailsDisplay').html(optionDetailsHtml);
            },
            error: function(error) {
                console.error("Error fetching option details:", error);
            }
        });
    }

 // Add a click event listener to option list items
$(document).on('click', '.option-item', function() {
    const OptionID = $(this).data('id');
    fetchOptionDetails(OptionID);
    // Add AJAX call here to store user choice
    let userCookie = getCookie("userCookie"); // Get the user cookie
    $.ajax({
        type: 'POST',
        url: `${API_URL}/store_user_choice`, // Replace with your actual backend URL
        data: JSON.stringify({
            option_id: OptionID,
            user_cookie: userCookie
        }),
        contentType: "application/json; charset=utf-8",
        success: function(response) {
            console.log("User choice stored:", response);
        },
        error: function(error) {
            console.error("Error storing user choice:", error);
        }
    });
});

// Get a random dilemma when the button is clicked
$('#getRandomDilemmaButton').click(function() {
    fetchRandomDilemma();
});

});

</script>