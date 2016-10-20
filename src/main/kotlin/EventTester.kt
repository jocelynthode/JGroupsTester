import net.sourceforge.argparse4j.ArgumentParsers
import net.sourceforge.argparse4j.inf.ArgumentParserException
import org.apache.logging.log4j.LogManager
import org.jgroups.*
import java.time.LocalDateTime
import java.time.ZoneOffset
import java.util.*
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit

/**
 * This Class connects to a cluster, waits for other peers to join and then sends a number of events
 *
 * This implementation uses the SEQUENCER Channel. This uses Total Order and UDP
 *
 * @author Jocelyn Thode
 */
class EventTester(val eventsToSend: Int, val peerNumber: Int, val rate: Long, protocolStack: String,
                  val startTime: Long) : ReceiverAdapter() {

    val logger = LogManager.getLogger(this.javaClass)!!

    var channel = JChannel(protocolStack)
    val TOTAL_MESSAGES = peerNumber * eventsToSend
    var deliveredMessages = 0
    val runJGroups = Runnable {
        var eventsSent = 0

        logger.info("Sending: $eventsToSend events (rate: 1 every ${rate}ms)")
        while (eventsSent != eventsToSend) {
            Thread.sleep(rate)
            val msg = Message(null, null, "${UUID.randomUUID()}")
            logger.info("Sending: ${msg.`object`}")
            channel.send(msg)
            eventsSent++
        }
        var i = 0
        while (i < 120) {
            logger.debug("Events not yet delivered: {}", (TOTAL_MESSAGES - deliveredMessages))
            Thread.sleep(10000)
            i++
        }
        stop()
    }

    fun start() {
        channel.receiver = this
        channel.connect("EventCluster")
        logger.info(channel.address.toString())
        logger.info("Peer Number: $peerNumber")

        //Start test when everyone is here
        //while (channel.view.size() < peerNumber) {
            Thread.sleep(10000)
        //}
        val scheduler = Executors.newScheduledThreadPool(1)
        scheduler.schedule(runJGroups, scheduleAt(startTime), TimeUnit.MILLISECONDS)
    }

    private fun scheduleAt(date: Long): Long {
        if (date < System.currentTimeMillis()) {
            logger.warn("Time given was smaller than current time, running JGroups immediately, but some events might get lost")
            return 0
        } else {
            logger.debug("JGroups will start at {} UTC+2",
                    LocalDateTime.ofEpochSecond((date / 1000), 0, ZoneOffset.ofHours(2)))
            return (date - System.currentTimeMillis())
        }
    }

    fun stop() {
        channel.disconnect()
        logger.info("Ratio of events delivered: ${deliveredMessages / TOTAL_MESSAGES.toDouble()}")
        logger.info("Messages sent: ${channel.sentMessages}")
        logger.info("Messages received: ${channel.receivedMessages}")
        System.exit(0)
    }

    override fun viewAccepted(newView: View) {
        logger.debug("** size: ${newView.size()} ** view: $newView")
    }

    override fun receive(msg: Message) {
        logger.info("Delivered: ${msg.`object`}")
        deliveredMessages++
        if (deliveredMessages >= TOTAL_MESSAGES) {
            logger.info("All events delivered !")
            stop()
        }
    }
}

fun main(args: Array<String>) {
    val parser = ArgumentParsers.newArgumentParser("EpTO tester")
    parser.defaultHelp(true)
    parser.addArgument("peerNumber").help("Peer number")
            .type(Integer.TYPE)
            .setDefault(35)
    parser.addArgument("protocolStack").help("XML file containing the protocol stack configuration")
    parser.addArgument("scheduleAt").help("Schedule Jgroups to start at a specific time in milliseconds")
            .type(Long::class.java)
    parser.addArgument("-e", "--events").help("Number of events to send")
            .type(Integer.TYPE)
            .setDefault(12)
    parser.addArgument("-r", "--rate").help("Time between each event broadcast in ms")
            .type(Long::class.java)
            .setDefault(1000L)

    try {
        val res = parser.parseArgs(args)
        val eventTester = EventTester(res.getInt("events"), res.getInt("peerNumber"), res.getLong("rate"),
                res.getString("protocolStack"), res.getLong("scheduleAt"))
        eventTester.start()
        while (true) Thread.sleep(500)
    } catch (e: ArgumentParserException) {
        parser.handleError(e)
    }
}
