<script type="text/javascript"> 
jQuery(document).ready(function($) {

    // --------------------------------------------------------------------
    // Function definitions
    // --------------------------------------------------------------------

    // Function to generate a unique ID
    function generateUniqueID() {
        return 'xxxx-xxxx-4xxx-yxxx-xxxx'.replace(/[xy]/g, function(c) {
            const r = (Math.random() * 16) | 0,
                v = c === 'x' ? r : (r & 0x3) | 0x8;
            return v.toString(16);
        });
    }

    // Function to get a cookie
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

    // Function to set a cookie
    function setCookie(cname, cvalue, exdays) {
        const d = new Date();
        d.setTime(d.getTime() + (exdays * 24 * 60 * 60 * 1000));
        let expires = "expires="+d.toUTCString();
        document.cookie = cname + "=" + cvalue + ";" + expires + ";path=/";
    }

    
    // Function to fetch unviewed dilemmas
    function fetchUnviewedDilemmas(userCookie, userId, callback) {
        let dataToSend = {
            cookie_id: userCookie
        };
        if (userId) {
            dataToSend.user_id = userId;
        }
 
        $.ajax({
            type: 'POST',
            url: `${API_URL}/get_unviewed_dilemmas`,
            data: JSON.stringify({
                user_id: userId, // include the userId here
                cookie_id: userCookie
            }),
            contentType: "application/json; charset=utf-8",
            success: function(response) {
                // your existing success logic here
            },
            error: function(error) {
                console.error("Error fetching unviewed dilemmas:", error);
            }
        });
    }
        
    // Function to update toggle setting in the backend
    function updateToggleSetting(toggleName, state) {
        $.ajax({
            type: 'POST',
            url: `${API_URL}/update_toggle_setting`,
            data: JSON.stringify({
                cookie_id: userCookie, // corrected to cookie_id
                toggle_name: toggleName,
                state: state
            }),
            contentType: "application/json; charset=utf-8",
            success: function(response) {
                console.log("Toggle setting updated:", response);
            }
        });
    }
    
    // Function to fetch random dilemma
    function fetchRandomDilemma(userId, isRandom, isConsequential) {
        let dataToSend = {
            cookie_id: userCookie,
            user_id: userId,         // Include userId
            is_random: isRandom,     // Include isRandom
            is_consequential: isConsequential  // Include isConsequential
        };
    
        $.ajax({
            type: 'POST',
            url: `${API_URL}/get_dilemma`,
            data: JSON.stringify(dataToSend),
            contentType: "application/json; charset=utf-8",
            success: function(response) {
                if(response.message) {
                    $('#randomDilemmaDisplay').html('<h3>' + response.message + '</h3>');
                    return;
                }
                const dilemma = response.dilemma;
                currentDilemmaID = dilemma.id; // Store the current dilemma ID
                console.log("Set currentDilemmaID:", currentDilemmaID); // Debug log

                // Display the dilemma
                let dilemmaHtml = `<h3>${dilemma.question}</h3><p><h4>Choose an option</h4></p><ul>`;
                dilemma.options.forEach(function(option) {
                    dilemmaHtml += `<h4><li class="option-item" data-id="${option.id}">${option.text}</li></h4>`;
                });
                dilemmaHtml += '</ul>';
                $('#randomDilemmaDisplay').html(dilemmaHtml);

                // Clear the option details
                $('#optionDetailsDisplay').html('');

                // Mark this dilemma as viewed
                // markDilemmaAsViewed(dilemma.id, userCookie);
            },
            error: function(error) {
                if (error.status === 404) {
                    $('#randomDilemmaDisplay').html('<h3>No more dilemmas to display.</h3>');
                } else {
                    console.error("Error fetching random dilemma:", error);
                }
            }
        });
    }

    // Function to mark a dilemma as viewed
    function markDilemmaAsViewed(dilemmaId, userCookie) {
        $.ajax({
            type: 'POST',
            url: `${API_URL}/view_dilemma/${dilemmaId}`,
            data: JSON.stringify({
                cookie_id: userCookie
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


    // --------------------------------------------------------------------
    // Event handlers and API calls
    // --------------------------------------------------------------------

    // Replace this with your deployed API URL
    const API_URL = 'https://ethiquest-builder.onrender.com/customer';

    let currentDilemmaID = null; 
    let userCookie = getCookie("userCookie");

    if (userCookie === "") {
        userCookie = generateUniqueID();
        setCookie("userCookie", userCookie, 365);
    }

    // Initialize these to defaults
    let isRegistered = false;
    let userId = null;
    let isRandom = false;
    let isConsequential = false;

    let userQueryParameter = isRegistered ? `user_id=${userId}` : `cookie_id=${userCookie}`;
    
    // Fetch initial toggle settings and then fetch unviewed dilemmas
    $.ajax({
        type: 'GET',
        url: `${API_URL}/get_toggle_settings`,
        data: userQueryParameter,
        success: function(response) {
            userId = response.user;  // Store user ID for future use

            // Update the states of the toggles
            isRandom = response.random;
            isConsequential = response.consequential;

            // Set initial states for the toggles
            if (response.random) {
                $('#randomToggle').css({ left: '60px' }).text('ON');
            }
            if (response.consequential) {
                $('#consequentialToggle').css({ left: '60px' }).text('ON');
            }

            // Fetch unviewed dilemmas after getting user ID
            fetchUnviewedDilemmas(userCookie, userId);
        }
    });

    // Event listeners for toggle buttons
    $('.toggle-button').click(function() {
        const toggleId = $(this).attr('id');
        if ($(this).css('left') === '60px') {
            $(this).css({ left: '0px' }).text('OFF');
            updateToggleSetting(toggleId, false);
        } else {
            $(this).css({ left: '60px' }).text('ON');
            updateToggleSetting(toggleId, true);
        }
    });


    // Add a click event listener to option list items
    $(document).on('click', '.option-item', function() {
        const OptionID = $(this).data('id');
        fetchOptionDetails(OptionID);

        console.log("Sending data:", {  // Debug log
            option_id: OptionID,
            user_cookie: userCookie,
            dilemma_id: currentDilemmaID
        });

        console.log("Current Dilemma ID before sending:", currentDilemmaID); // Debug log

        $.ajax({
            type: 'POST',
            url: `${API_URL}/store_user_choice`, // Replace with your actual backend URL
            data: JSON.stringify({
                option_id: OptionID,
                user_cookie: userCookie,
                dilemma_id: currentDilemmaID  // Send the current dilemma ID
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
        fetchRandomDilemma(userId, isRandom, isConsequential);
    });
});
</script>